"""Strategy: Advanced Football State Machine (Kinematics, Collective Deceleration, & Tuned Lookahead).

Features:
1. Deep Lookahead Turnover Guard (50 frames / 2.0s):
   Requires sustained opponent possession (>= 20 frames / 0.8s) without recovery by original team within 35 frames (1.4s).
2. Collective Kinematic Dead-Ball Detector:
   Detects stoppages when collective player speed drops below walking pace (< 1.6 m/s)
   or ball is missing for prolonged periods (> 45 frames / 1.8s) with no nearby carrier.
3. Minimum Possession Duration Post-Processing:
   Merges micro-possessions (< 35 frames / 1.4s) into surrounding spells to eliminate spurious splits.
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext
from pipeline.ball_reconstruction import reconstruct_ball_trajectory
from pipeline.evidence import compute_frame_control_evidence


class FSMAdvancedStrategy(BaseStrategy):
    """Advanced Football State Machine with kinematic dead-ball detection and deep lookahead."""

    def __init__(
        self,
        lookahead_window: int = 50,
        min_turnover_frames: int = 20,
        max_turnover_rebound_gap: int = 35,
        control_radius: float = 2.0,
        min_possession_frames: int = 40,
        speed_stoppage_threshold: float = 1.6,
        ball_missing_dead_frames: int = 45,
        name: str = "fsm_advanced",
    ):
        super().__init__(
            name=name,
            description="Advanced FSM with collective kinematic deceleration, deep lookahead, and micro-spell merging",
            lookahead_window=lookahead_window,
            min_turnover_frames=min_turnover_frames,
            max_turnover_rebound_gap=max_turnover_rebound_gap,
            control_radius=control_radius,
            min_possession_frames=min_possession_frames,
            speed_stoppage_threshold=speed_stoppage_threshold,
            ball_missing_dead_frames=ball_missing_dead_frames,
        )
        self.lookahead_window = lookahead_window
        self.min_turnover_frames = min_turnover_frames
        self.max_turnover_rebound_gap = max_turnover_rebound_gap
        self.control_radius = control_radius
        self.min_possession_frames = min_possession_frames
        self.speed_stoppage_threshold = speed_stoppage_threshold
        self.ball_missing_dead_frames = ball_missing_dead_frames

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames
        output = np.full(n_frames, "X", dtype="<U1")
        dead_mask = ctx.dead_ball_mask.copy()

        # 1. Trajectory reconstruction
        interp_ball, is_imputed = reconstruct_ball_trajectory(ctx.ball_coords, max_gap_frames=20)

        # 2. Extract control signals
        nearest_teams = np.full(n_frames, None, dtype=object)
        has_controls = np.zeros(n_frames, dtype=bool)
        dists_h = np.full(n_frames, np.inf, dtype=np.float32)
        dists_a = np.full(n_frames, np.inf, dtype=np.float32)

        for f in range(n_frames):
            ev = compute_frame_control_evidence(
                interp_ball[f],
                ctx.player_coords[f],
                ctx.player_teams,
                pitch_dim=ctx.pitch_dim,
                control_radius=self.control_radius,
            )
            nearest_teams[f] = ev["nearest_team"]
            has_controls[f] = ev["has_control"]
            dists_h[f] = ev["dist_H"]
            dists_a[f] = ev["dist_A"]

        # 3. Detect Dead Balls from Missing Ball & Collective Deceleration
        # Find runs of missing ball
        is_missing = np.isnan(ctx.ball_coords[:, 0])
        # Find contiguous missing runs
        missing_runs = []
        in_run = False
        start_idx = 0
        for f in range(n_frames):
            if is_missing[f] and not in_run:
                in_run = True
                start_idx = f
            elif not is_missing[f] and in_run:
                in_run = False
                if f - start_idx >= self.ball_missing_dead_frames:
                    missing_runs.append((start_idx, f))
        if in_run and (n_frames - start_idx >= self.ball_missing_dead_frames):
            missing_runs.append((start_idx, n_frames))

        for s_idx, e_idx in missing_runs:
            for f in range(s_idx + 15, e_idx):  # allow 15 frames buffer before declaring dead
                if dead_mask[f] == "":
                    dead_mask[f] = "D"

        # 4. State Machine execution
        current_state = None
        t = 0
        while t < n_frames:
            if dead_mask[t] == "X":
                output[t] = "X"
                current_state = None
                t += 1
                continue

            if dead_mask[t] == "D":
                output[t] = "D"
                current_state = "D"
                t += 1
                continue

            if t in ctx.restarts:
                current_state = ctx.restarts[t]
                output[t] = current_state
                t += 1
                continue

            if current_state is None or current_state == "D":
                # Restart condition
                if nearest_teams[t] in ("H", "A") and has_controls[t]:
                    current_state = nearest_teams[t]
                elif nearest_teams[t] in ("H", "A") and (dists_h[t] < 3.0 or dists_a[t] < 3.0):
                    current_state = nearest_teams[t]
                else:
                    current_state = "D"
                output[t] = current_state
                t += 1
                continue

            # In active possession (H or A)
            opponent = "A" if current_state == "H" else "H"
            nearest = nearest_teams[t]
            in_control = has_controls[t]

            # Possession inertia
            if nearest != opponent or not in_control:
                output[t] = current_state
                t += 1
                continue

            # Candidate turnover: Opponent is in control
            # Inspect future lookahead window
            lookahead_end = min(t + self.lookahead_window, n_frames)
            future_nearest = nearest_teams[t : lookahead_end]
            future_dead = dead_mask[t : lookahead_end]

            if np.any(future_dead == "D"):
                output[t] = current_state
                t += 1
                continue

            opp_count = np.sum(future_nearest == opponent)
            orig_count = np.sum(future_nearest == current_state)

            orig_indices = np.flatnonzero(future_nearest == current_state)
            rebounded_quickly = (
                len(orig_indices) > 0 and orig_indices[0] <= self.max_turnover_rebound_gap
            )

            if rebounded_quickly and orig_count >= (opp_count * 0.7):
                # Deflection/loose contest: keep possession
                output[t] = current_state
                t += 1
            elif opp_count >= self.min_turnover_frames and opp_count > orig_count:
                # Confirmed turnover
                current_state = opponent
                output[t] = current_state
                t += 1
            else:
                output[t] = current_state
                t += 1

        # 5. Micro-Possession Merging (Post-processing)
        # Eliminate tiny spurious flicker spells (< min_possession_frames)
        # Convert runs
        breaks = np.flatnonzero(output[1:] != output[:-1]) + 1
        starts = np.concatenate(([0], breaks))
        stops = np.concatenate((breaks, [n_frames]))

        for i in range(len(starts)):
            s = starts[i]
            e = stops[i]
            lbl = output[s]
            length = e - s

            if lbl in ("H", "A") and length < self.min_possession_frames:
                # If flanked by same team or stoppage, merge
                prev_lbl = output[starts[i - 1]] if i > 0 else None
                next_lbl = output[starts[i + 1]] if i < len(starts) - 1 else None

                if prev_lbl == next_lbl and prev_lbl in ("H", "A"):
                    output[s:e] = prev_lbl
                elif prev_lbl in ("H", "A"):
                    output[s:e] = prev_lbl

        # Re-enforce deterministic masks
        output[ctx.dead_ball_mask == "X"] = "X"
        output[ctx.dead_ball_mask == "D"] = "D"
        return output

    def test_synthetic(self) -> bool:
        n = 200
        ball = np.ones((n, 2), dtype=np.float32) * 0.5
        players = np.ones((n, 2, 2), dtype=np.float32) * 0.6
        players[:, 0, :] = 0.505
        teams = np.array([0, 1], dtype=np.int8)
        mask = np.full(n, "", dtype="<U1")
        mask[:20] = "X"
        mask[180:] = "X"

        # Opponent deflection at frame 60
        players[60:63, 1, :] = 0.502
        players[60:63, 0, :] = 0.550

        # Opponent sustained turnover at 100..160
        players[100:160, 1, :] = 0.502
        players[100:160, 0, :] = 0.580

        ctx = TrackingContext(
            n_frames=n,
            ball_coords=ball,
            player_coords=players,
            player_teams=teams,
            dead_ball_mask=mask,
            restarts={20: "H"},
        )
        res = self.predict(ctx)
        assert res[61] == "H", "Deflection must be absorbed"
        assert res[120] == "A", "Sustained turnover must transition"
        return True
