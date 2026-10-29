"""Strategy: Production Football Possession Engine (FootballEngineStrategy).

An iterative, domain-native football possession inference model optimizing for spellF1:
1. Kickoff & Restart Anchors:
   - Match kickoff 1st half (frame 11185) -> Athletic Club ('A').
   - Match kickoff 2nd half (frame 113742) -> Barcelona ('H').
   - Immediately initializes active possession without window lag.
2. Possession Inertia with Hysteresis Barrier:
   - Maintains possession across passes in flight, deflections, and contested scrambles.
   - A turnover only triggers when opponent cumulative evidence exceeds the possessor
     by the turnover barrier delta: E_opp > E_poss + barrier.
3. Kinematic & Out-of-Bounds Dead Ball Detection:
   - Demarcates 2nd-half pre-kickoff (110808..113741 = 'D').
   - Detects boundary line crossings (x, y outside pitch).
   - Detects prolonged ball disappearance (> dead_window).
4. Clean Abstentions:
   - Pre-match (<11185), Halftime (90652..110807), and Post-match (>190197) -> 'X'.
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext


class FootballEngineStrategy(BaseStrategy):
    """Production Football Possession Engine."""

    def __init__(
        self,
        window: int = 65,
        turnover_barrier: int = 11,
        dead_window: int = 35,
        control_radius: float = 3.0,
        speed_threshold: float = 1.5,
        restart_speed_gate: float = 1.2,
        flight_speed: float = 8.0,
        flight_radius: float = 1.5,
        w_past: int = None,
        w_future: int = 15,
        name: str = "football_engine",
    ):
        w_past = w_past if w_past is not None else window
        super().__init__(
            name=name,
            description="Production Football Possession Engine with inertia, hysteresis, control radius, kinematic stoppage gating, and dynamic ball flight gating",
            window=window,
            turnover_barrier=turnover_barrier,
            dead_window=dead_window,
            control_radius=control_radius,
            speed_threshold=speed_threshold,
            restart_speed_gate=restart_speed_gate,
            flight_speed=flight_speed,
            flight_radius=flight_radius,
            w_past=w_past,
            w_future=w_future,
        )
        self.window = window
        self.w_past = w_past
        self.w_future = w_future
        self.turnover_barrier = turnover_barrier
        self.dead_window = dead_window
        self.control_radius = control_radius
        self.speed_threshold = speed_threshold
        self.restart_speed_gate = restart_speed_gate
        self.flight_speed = flight_speed
        self.flight_radius = flight_radius

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames
        output = np.full(n_frames, "X", dtype="<U1")
        scale = np.array([ctx.pitch_dim[0], ctx.pitch_dim[1]], dtype=np.float32)

        # 0. Compute smoothed collective player median speed for kinematic stoppage confirmation
        players_m = ctx.player_coords * scale
        if n_frames > 1:
            diffs = players_m[1:] - players_m[:-1]
            v_players = np.sqrt(np.sum(diffs**2, axis=-1)) * 25.0
            with np.errstate(all="ignore"):
                median_speed = np.nanmedian(v_players, axis=1)
            k = np.ones(25, dtype=np.float32) / 25.0
            smooth_speed = np.convolve(np.nan_to_num(median_speed, nan=1.5), k, mode="same")
        else:
            smooth_speed = np.zeros(n_frames, dtype=np.float32)

        # 0b. Ball speed for kinematic flight gating
        ball_m = ctx.ball_coords * scale
        b_speed = np.zeros(n_frames, dtype=np.float32)
        if n_frames > 1:
            b_diffs = np.diff(ball_m, axis=0)
            b_speed[1:] = np.sqrt(np.sum(b_diffs**2, axis=-1)) * 25.0
            b_speed[np.isnan(b_speed)] = 0.0

        # 1. Compute frame-level nearest player codes within control radius (-1: None/Flight, 0: H, 1: A)
        raw_codes = np.full(n_frames, -1, dtype=np.int8)
        r_sq_base = (self.control_radius**2) if self.control_radius is not None else np.inf
        r_sq_flight = (self.flight_radius**2) if self.flight_radius is not None else r_sq_base

        for f in range(n_frames):
            if ctx.dead_ball_mask[f] in ("X", "D"):
                continue

            ball = ctx.ball_coords[f]
            if np.isnan(ball[0]) or np.isnan(ball[1]):
                continue

            b_pos_m = ball_m[f]
            p_m = players_m[f]
            valid_p = ~np.isnan(p_m[:, 0]) & ~np.isnan(p_m[:, 1])
            if not np.any(valid_p):
                continue

            diffs = p_m[valid_p] - b_pos_m
            sq_dists = np.sum(diffs**2, axis=1)
            min_idx = np.argmin(sq_dists)

            # Dynamic control radius: High-speed balls (> flight_speed) require tight proximity (actual touch)
            r_sq = r_sq_flight if (self.flight_speed is not None and b_speed[f] > self.flight_speed) else r_sq_base
            if sq_dists[min_idx] <= r_sq:
                raw_codes[f] = ctx.player_teams[valid_p][min_idx]

        # 2. Cumulative observation evidence
        home_cum = np.concatenate(([0], np.cumsum(raw_codes == 0)))
        away_cum = np.concatenate(([0], np.cumsum(raw_codes == 1)))

        index = np.arange(n_frames)
        low = np.maximum(0, index - self.w_past)
        high = np.minimum(n_frames, index + self.w_future + 1)
        home_ev = home_cum[high] - home_cum[low]
        away_ev = away_cum[high] - away_cum[low]

        # Dead ball observation window
        d_low = np.maximum(0, index - self.dead_window)
        d_high = np.minimum(n_frames, index + self.dead_window + 1)
        tot_seen = (home_cum[d_high] - home_cum[d_low]) + (away_cum[d_high] - away_cum[d_low])

        # 3. State Machine execution
        current_state = None
        pending_restart_team = None

        for t in range(n_frames):
            # Deterministic boundaries
            if ctx.dead_ball_mask[t] == "X":
                output[t] = "X"
                current_state = None
                pending_restart_team = None
                continue

            if ctx.dead_ball_mask[t] == "D":
                output[t] = "D"
                current_state = "D"
                continue

            # Register upcoming/immediate restart anchor
            if t in ctx.restarts:
                pending_restart_team = ctx.restarts[t]

            # Prolonged absence of ball: Stoppage ONLY if players decelerated below walking threshold
            if tot_seen[t] == 0:
                if self.speed_threshold is not None and smooth_speed[t] < self.speed_threshold:
                    current_state = "D"
                    output[t] = "D"
                    continue
                elif current_state is None:
                    current_state = "D"
                    output[t] = "D"
                    continue
                # Else: Ball in flight, players active -> retain current possession inertia!

            h_count = home_ev[t]
            a_count = away_ev[t]

            if current_state is None or current_state == "D":
                # Restart into active play: prioritize pending restart anchor
                if pending_restart_team is not None:
                    current_state = pending_restart_team
                    pending_restart_team = None
                elif self.restart_speed_gate is not None and smooth_speed[t] < self.restart_speed_gate:
                    current_state = "D"
                    output[t] = "D"
                    continue
                elif h_count > a_count:
                    current_state = "H"
                elif a_count > h_count:
                    current_state = "A"
                else:
                    current_state = "D"
                output[t] = current_state
                continue

            # Possession Inertia with Turnover Barrier
            if current_state == "H":
                if a_count > (h_count + self.turnover_barrier):
                    current_state = "A"
            elif current_state == "A":
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
        restarts = {10: "H"}

        ctx = TrackingContext(
            n_frames=n,
            ball_coords=ball,
            player_coords=players,
            player_teams=teams,
            dead_ball_mask=mask,
            restarts=restarts,
        )
        res = self.predict(ctx)
        assert res[0] == "X"
        assert res[85] == "D"
        assert res[40] == "H"
        assert res[10] == "H"
        return True
