"""Strategy: Inertia-Hysteresis State Machine (I-HSM).

Combines:
1. Multi-scale cumulative observation evidence (cumulative nearest-player control).
2. Asymmetric Possession Inertia Hysteresis:
   - When in STATE_H, transitioning to STATE_A requires opponent evidence to exceed
     home evidence by an explicit turnover barrier: E_A(t) > E_H(t) + delta.
   - Prevents 50/50 loose-ball scrambles and deflections from flipping possession.
3. Dual-scale Dead-Ball Demarcation:
   - Preserves deterministic boundaries and Smart Tagging set-piece windows.
   - Detects prolonged ball disappearance and boundary crossings.
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext
from pipeline.ball_reconstruction import reconstruct_ball_trajectory
from pipeline.evidence import compute_frame_control_evidence


class FSMHysteresisStrategy(BaseStrategy):
    """Inertia-Hysteresis State Machine."""

    def __init__(
        self,
        window: int = 40,
        turnover_barrier: int = 15,
        dead_window: int = 50,
        name: str = "fsm_hysteresis",
    ):
        super().__init__(
            name=name,
            description="Inertia-Hysteresis State Machine with cumulative evidence and turnover barrier",
            window=window,
            turnover_barrier=turnover_barrier,
            dead_window=dead_window,
        )
        self.window = window
        self.turnover_barrier = turnover_barrier
        self.dead_window = dead_window

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames
        output = np.full(n_frames, "X", dtype="<U1")

        # 1. Compute frame-level nearest player codes (-1: None/D, 0: H, 1: A)
        raw_codes = np.full(n_frames, -1, dtype=np.int8)
        scale = np.array([ctx.pitch_dim[0], ctx.pitch_dim[1]], dtype=np.float32)

        for f in range(n_frames):
            if ctx.dead_ball_mask[f] in ("X", "D"):
                continue

            ball = ctx.ball_coords[f]
            if np.isnan(ball[0]) or np.isnan(ball[1]):
                continue

            ball_m = ball * scale
            players_m = ctx.player_coords[f] * scale
            valid_p = ~np.isnan(players_m[:, 0]) & ~np.isnan(players_m[:, 1])
            if not np.any(valid_p):
                continue

            diffs = players_m[valid_p] - ball_m
            dists = np.sum(diffs**2, axis=1)
            teams = ctx.player_teams[valid_p]
            raw_codes[f] = teams[np.argmin(dists)]

        # 2. Cumulative evidence arrays
        home_cum = np.concatenate(([0], np.cumsum(raw_codes == 0)))
        away_cum = np.concatenate(([0], np.cumsum(raw_codes == 1)))

        index = np.arange(n_frames)
        low = np.maximum(0, index - self.window)
        high = np.minimum(n_frames, index + self.window + 1)
        home_ev = home_cum[high] - home_cum[low]
        away_ev = away_cum[high] - away_cum[low]

        # Dead ball window
        d_low = np.maximum(0, index - self.dead_window)
        d_high = np.minimum(n_frames, index + self.dead_window + 1)
        tot_seen = (home_cum[d_high] - home_cum[d_low]) + (away_cum[d_high] - away_cum[d_low])

        # 3. State Machine with Possession Inertia & Hysteresis Barrier
        current_state = None  # 'H', 'A', or 'D'

        for t in range(n_frames):
            # Deterministic boundaries
            if ctx.dead_ball_mask[t] == "X":
                output[t] = "X"
                current_state = None
                continue

            if ctx.dead_ball_mask[t] == "D":
                output[t] = "D"
                current_state = "D"
                continue

            if t in ctx.restarts:
                current_state = ctx.restarts[t]
                output[t] = current_state
                continue

            # Prolonged absence of ball -> dead ball
            if tot_seen[t] == 0:
                current_state = "D"
                output[t] = "D"
                continue

            h_count = home_ev[t]
            a_count = away_ev[t]

            if current_state is None or current_state == "D":
                # Restart into active possession
                if h_count > a_count:
                    current_state = "H"
                elif a_count > h_count:
                    current_state = "A"
                else:
                    current_state = "D"
                output[t] = current_state
                continue

            # State persistence / turnover barrier
            if current_state == "H":
                # Requires Away evidence to overcome barrier
                if a_count > (h_count + self.turnover_barrier):
                    current_state = "A"
            elif current_state == "A":
                # Requires Home evidence to overcome barrier
                if h_count > (a_count + self.turnover_barrier):
                    current_state = "H"

            output[t] = current_state

        # Enforce deterministic boundaries
        output[ctx.dead_ball_mask == "X"] = "X"
        output[ctx.dead_ball_mask == "D"] = "D"
        return output

    def test_synthetic(self) -> bool:
        n = 100
        ball = np.ones((n, 2)) * 0.5
        players = np.ones((n, 2, 2)) * 0.6
        players[:, 0, :] = 0.505
        teams = np.array([0, 1])
        mask = np.full(n, "", dtype="<U1")
        mask[:10] = "X"
        mask[80:] = "D"

        ctx = TrackingContext(n_frames=n, ball_coords=ball, player_coords=players, player_teams=teams, dead_ball_mask=mask)
        res = self.predict(ctx)
        assert res[0] == "X"
        assert res[85] == "D"
        assert res[40] == "H"
        return True
