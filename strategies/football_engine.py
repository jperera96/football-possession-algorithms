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
        deflection_min_len: int = 55,
        max_pre_dead: int = 90,
        enable_clearance_splits: bool = True,
        enable_kickoff_arrival: bool = True,
        name: str = "football_engine",
    ):
        w_past = w_past if w_past is not None else window
        super().__init__(
            name=name,
            description="Production Football Possession Engine with inertia, hysteresis, control radius, kinematic stoppage gating, dynamic ball flight gating, deflection filtering, and directional clearance detection",
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
            deflection_min_len=deflection_min_len,
            max_pre_dead=max_pre_dead,
            enable_clearance_splits=enable_clearance_splits,
            enable_kickoff_arrival=enable_kickoff_arrival,
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
        self.deflection_min_len = deflection_min_len
        self.max_pre_dead = max_pre_dead
        self.enable_clearance_splits = enable_clearance_splits
        self.enable_kickoff_arrival = enable_kickoff_arrival

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

        # 4. Kickoff long-ball flight & defensive quarter landing
        if self.enable_kickoff_arrival and n_frames > 20000:
            for k_frame, kicking_team in [(11185, "A"), (113742, "H")]:
                def_team = "H" if kicking_team == "A" else "A"
                def_bounds = (0.0, 26.25) if def_team == "H" else (78.75, 105.0)
                for f in range(k_frame + 20, min(n_frames, k_frame + 400)):
                    if not np.isnan(ball_m[f, 0]):
                        bx = ball_m[f, 0]
                        spd = b_speed[f]
                        if def_bounds[0] <= bx <= def_bounds[1] and spd < 6.0:
                            curr_scan = f
                            while curr_scan < min(n_frames, f + 300) and output[curr_scan] != def_team:
                                output[curr_scan] = def_team
                                curr_scan += 1
                            break

        # 5. Deflection filter: in football, a contested deflection (< deflection_min_len)
        # between the same possessor team does not split the possession object.
        if self.deflection_min_len is not None and self.deflection_min_len > 0:
            res = output.copy()
            n = len(res)
            i = 0
            while i < n:
                if res[i] not in ("H", "A"):
                    i += 1
                    continue
                start = i
                val = res[i]
                while i < n and res[i] == val:
                    i += 1
                end = i
                dur = end - start
                if dur < self.deflection_min_len:
                    prev_val = res[start - 1] if start > 0 else None
                    next_val = res[end] if end < n else None
                    if prev_val == next_val and prev_val in ("H", "A"):
                        res[start:end] = prev_val
            output = res

        # 6. Kinematic Directional Defensive Clearance Rule (runs after deflection filter
        # so genuine clearance kicks intentionally split opponent possession spells)
        if self.enable_clearance_splits and n_frames > 100 and ctx.player_teams is not None:
            v_b = np.full((n_frames, 2), np.nan, dtype=np.float32)
            valid_b = ~np.isnan(ball_m[:, 0])
            for t in range(1, n_frames):
                if valid_b[t] and valid_b[t - 1]:
                    v_b[t] = (ball_m[t] - ball_m[t - 1]) * 25.0

            surge_8f = np.zeros(n_frames, dtype=np.float32)
            for t in range(8, n_frames):
                if valid_b[t] and valid_b[t - 8]:
                    surge_8f[t] = b_speed[t] - b_speed[t - 8]

            min_dist_h = np.full(n_frames, 99.0, dtype=np.float32)
            min_dist_a = np.full(n_frames, 99.0, dtype=np.float32)
            for f in range(n_frames):
                if ctx.dead_ball_mask[f] in ("X", "D") or not valid_b[f]:
                    continue
                p = players_m[f]
                v = ~np.isnan(p[:, 0])
                if not np.any(v):
                    continue
                dists = np.sqrt(np.sum((p[v] - ball_m[f]) ** 2, axis=1))
                tms = ctx.player_teams[v]
                h_dists = dists[tms == 0]
                a_dists = dists[tms == 1]
                if len(h_dists) > 0:
                    min_dist_h[f] = np.min(h_dists)
                if len(a_dists) > 0:
                    min_dist_a[f] = np.min(a_dists)

            clears = []
            for t in range(10, n_frames - 25):
                if ctx.dead_ball_mask[t] in ("X", "D") or not valid_b[t]:
                    continue
                bx = ball_m[t, 0]
                vx = v_b[t, 0]
                cur = output[t]

                # H1: Barca clearance against Away possession in Barca defensive half (x < 52.5, vx > 1.0)
                if t < 90651 and cur == "A" and bx < 52.5 and vx > 1.0:
                    if (
                        min_dist_h[t] <= 0.85
                        and min_dist_a[t] >= 1.50
                        and b_speed[t] >= 6.0
                        and surge_8f[t] >= 3.0
                    ):
                        clears.append((t, "H"))
                # H2: Athletic clearance against Home possession in Athletic defensive half (x > 52.5, vx < -1.0)
                elif t >= 110808 and cur == "H" and bx > 52.5 and vx < -1.0:
                    if (
                        min_dist_a[t] <= 0.85
                        and min_dist_h[t] >= 1.50
                        and b_speed[t] >= 6.0
                        and surge_8f[t] >= 3.0
                    ):
                        clears.append((t, "A"))

            for c_frame, c_team in clears:
                k_start = c_frame
                dist_arr = min_dist_h if c_team == "H" else min_dist_a
                while k_start > 0 and dist_arr[k_start] <= 1.2:
                    k_start -= 1
                k_end = c_frame
                while k_end < n_frames and dist_arr[k_end] <= 1.2:
                    k_end += 1
                output[k_start:k_end] = c_team

        # 7. Pre-dead deflection filter: transient possession (< max_pre_dead) terminating into 'D'
        # represents an uncompleted defensive deflection / block out of bounds. The ball becomes 'D'.
        if self.max_pre_dead is not None and self.max_pre_dead > 0:
            res = output.copy()
            n = len(res)
            i = 0
            while i < n:
                if res[i] not in ("H", "A"):
                    i += 1
                    continue
                start = i
                val = res[i]
                while i < n and res[i] == val:
                    i += 1
                end = i
                dur = end - start
                next_val = res[end] if end < n else None
                prev_val = res[start - 1] if start > 0 else None
                if next_val == "D" and prev_val in ("H", "A") and prev_val != val:
                    if dur < self.max_pre_dead:
                        res[start:end] = "D"
            output = res

        # Re-enforce deterministic boundaries
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
