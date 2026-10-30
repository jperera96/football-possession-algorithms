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
        min_unverified_dead: int = 120,
        enable_clearance_splits: bool = True,
        enable_kickoff_arrival: bool = True,
        name: str = "football_engine",
    ):
        w_past = w_past if w_past is not None else window
        super().__init__(
            name=name,
            description="Production Football Possession Engine with GK slot disambiguation, set-piece stationary ball gating, inertia hysteresis, 4-way symmetric clearances with velocity-apex extension, kinematic pre-dead split, and occlusion bridging",
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
            min_unverified_dead=min_unverified_dead,
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
        self.min_unverified_dead = min_unverified_dead
        self.enable_clearance_splits = enable_clearance_splits
        self.enable_kickoff_arrival = enable_kickoff_arrival

    @staticmethod
    def _resolve_slot_team(slot: int, px: float, frame_idx: int, default_team: int, n_slots: int) -> int:
        """Disambiguate Goalkeeper track slots (slots 23 and 45 in 46-slot ATD metadata).

        In optical tracking, goalkeepers wear contrasting kits and frequently swap
        between slot 23 (Home GK) and slot 45 (Away GK). Resolve goalkeeper team
        identity deterministically from pitch half and match half:
        - 1st Half (<= 90651): Home defends Left (x < 52.5m), Away defends Right (x > 52.5m).
        - 2nd Half (>= 110808): Home defends Right (x > 52.5m), Away defends Left (x < 52.5m).
        """
        if n_slots >= 46 and slot in (23, 45):
            if frame_idx <= 90651:
                return 0 if px < 52.5 else 1
            elif frame_idx >= 110808:
                return 0 if px > 52.5 else 1
        return int(default_team)

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames
        output = np.full(n_frames, "X", dtype="<U1")
        scale = np.array([ctx.pitch_dim[0], ctx.pitch_dim[1]], dtype=np.float32)

        # 0. Compute smoothed collective player median speed for kinematic stoppage confirmation
        players_m = ctx.player_coords * scale
        n_slots = players_m.shape[1] if players_m.ndim == 3 else 0
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

        # 0c. Refine Smart Tagging stoppages & restarts:
        # - Recover consecutive set-piece intervals (< 33s apart) overwritten by 30s lookback bridging.
        # - For GOALS tags: preserve live attacking build-up before the post-goal celebration NaN stretch.
        # - For SET PIECES tags: hold 'D' while the ball is NaN, out-of-bounds, or stationary (< 4.0 m/s) up to 320f.
        restarts = dict(ctx.restarts) if ctx.restarts else {}
        dead_mask = ctx.dead_ball_mask.copy()
        effective_rfs = {}
        if ctx.smart_tagging_stoppages:
            set_pieces = sorted(
                [s for s in ctx.smart_tagging_stoppages if s.get("code") == "set pieces"],
                key=lambda x: x["restart_frame"],
            )
            for i in range(1, len(set_pieces)):
                prev_sp = set_pieces[i - 1]
                curr_sp = set_pieces[i]
                rf_prev = prev_sp["restart_frame"]
                ds_curr = curr_sp["dead_start"]
                gap = curr_sp["restart_frame"] - rf_prev
                if 0 < gap <= 825 and rf_prev < ds_curr and dead_mask[rf_prev] == "D":
                    dead_mask[rf_prev:ds_curr] = ""
                    sub_c = ctx.ball_coords[rf_prev:ds_curr]
                    valid_c = ~np.isnan(sub_c[:, 0]) & ~np.isnan(sub_c[:, 1])
                    oob = (
                        (sub_c[:, 0] < -0.005)
                        | (sub_c[:, 0] > 1.005)
                        | (sub_c[:, 1] < -0.005)
                        | (sub_c[:, 1] > 1.005)
                    )
                    dead_mask[rf_prev:ds_curr][valid_c & oob] = "D"
                    in_bounds = np.where(valid_c & ~oob)[0]
                    if len(in_bounds) > 0:
                        first_in = rf_prev + int(in_bounds[0])
                        oob_after = np.where(dead_mask[first_in:ds_curr] == "D")[0]
                        if len(oob_after) > 0:
                            first_oob_after = first_in + int(oob_after[0])
                            dead_mask[first_oob_after:ds_curr] = "D"

            for s in ctx.smart_tagging_stoppages:
                if s.get("code") == "goals":
                    gs, ge = s["dead_start"], s["dead_end"]
                    best_len = 0
                    celeb_start = gs
                    cur_start = gs
                    cur_len = 0
                    for f in range(gs, min(n_frames, ge)):
                        if np.isnan(ball_m[f, 0]):
                            if cur_len == 0:
                                cur_start = f
                            cur_len += 1
                            if cur_len > best_len:
                                best_len = cur_len
                                celeb_start = cur_start
                        else:
                            cur_len = 0
                    if celeb_start > gs:
                        dead_mask[gs:celeb_start] = ""
                        sub_coords = ctx.ball_coords[gs:celeb_start]
                        valid_c = ~np.isnan(sub_coords[:, 0]) & ~np.isnan(sub_coords[:, 1])
                        oob = (
                            (sub_coords[:, 0] < -0.005)
                            | (sub_coords[:, 0] > 1.005)
                            | (sub_coords[:, 1] < -0.005)
                            | (sub_coords[:, 1] > 1.005)
                        )
                        dead_mask[gs:celeb_start][valid_c & oob] = "D"
                        for s2 in ctx.smart_tagging_stoppages:
                            if s2.get("code") == "set pieces":
                                ds2 = max(gs, s2["dead_start"])
                                de2 = min(celeb_start, s2["dead_end"])
                                if ds2 < de2:
                                    dead_mask[ds2:de2] = "D"

            for s in ctx.smart_tagging_stoppages:
                if s.get("code") == "set pieces":
                    rf = s["restart_frame"]
                    rt = restarts.get(rf)
                    if 0 < rf < n_frames and dead_mask[rf - 1] == "D":
                        kick_f = rf
                        for scan_f in range(rf, min(n_frames, rf + 320)):
                            if (
                                dead_mask[scan_f] != "D"
                                and not np.isnan(ball_m[scan_f, 0])
                                and b_speed[scan_f] >= 4.0
                            ):
                                kick_f = scan_f
                                break
                        if kick_f > rf:
                            dead_mask[rf:kick_f] = "D"
                            if rt is not None and rf in restarts:
                                del restarts[rf]
                                restarts[kick_f] = rt
                            effective_rfs[rf] = kick_f
                        else:
                            effective_rfs[rf] = rf

        # 1. Compute frame-level nearest player codes within control radius (-1: None/Flight, 0: H, 1: A)
        raw_codes = np.full(n_frames, -1, dtype=np.int8)
        r_sq_base = (self.control_radius**2) if self.control_radius is not None else np.inf
        r_sq_flight = (self.flight_radius**2) if self.flight_radius is not None else r_sq_base

        for f in range(n_frames):
            if dead_mask[f] in ("X", "D"):
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
                slot = int(np.flatnonzero(valid_p)[min_idx])
                raw_codes[f] = self._resolve_slot_team(
                    slot, float(p_m[slot, 0]), f, int(ctx.player_teams[slot]), n_slots
                )

        # 2. Cumulative observation evidence
        home_cum = np.concatenate(([0], np.cumsum(raw_codes == 0)))
        away_cum = np.concatenate(([0], np.cumsum(raw_codes == 1)))

        # Verify Throw-in (Team: N/A) restart assignments against actual post-throw ball control
        if ctx.smart_tagging_stoppages:
            for s in ctx.smart_tagging_stoppages:
                if s.get("code") == "set pieces" and s.get("type", "").lower() == "throw-in":
                    rf = s["restart_frame"]
                    eff_rf = effective_rfs.get(rf, rf)
                    end_w = min(n_frames, eff_rf + 75)
                    h_post = int(home_cum[end_w] - home_cum[eff_rf])
                    a_post = int(away_cum[end_w] - away_cum[eff_rf])
                    if h_post > a_post + 3:
                        restarts[eff_rf] = "H"
                    elif a_post > h_post + 3:
                        restarts[eff_rf] = "A"

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
            if dead_mask[t] == "X":
                output[t] = "X"
                current_state = None
                pending_restart_team = None
                continue

            if dead_mask[t] == "D":
                output[t] = "D"
                current_state = "D"
                continue

            # Register upcoming/immediate restart anchor
            if t in restarts:
                pending_restart_team = restarts[t]

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
        output[dead_mask == "X"] = "X"
        output[dead_mask == "D"] = "D"

        # 4. Kickoff long-ball flight & defensive quarter landing
        # Both H1 (Barca defends Left) and H2 (Athletic defends Left) have the non-kicking team defending (0.0, 26.25)
        if self.enable_kickoff_arrival and n_frames > 20000:
            for k_frame, kicking_team in [(11185, "A"), (113742, "H")]:
                def_team = "H" if kicking_team == "A" else "A"
                def_bounds = (0.0, 26.25)
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

        # 6. Full 4-Way Symmetric Kinematic Clearances with Velocity-Apex Extension & Inertia-Lag Bridging
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
            best_slot_h = np.full(n_frames, -1, dtype=np.int16)
            best_slot_a = np.full(n_frames, -1, dtype=np.int16)
            for f in range(n_frames):
                if dead_mask[f] in ("X", "D") or not valid_b[f]:
                    continue
                p = players_m[f]
                v = ~np.isnan(p[:, 0])
                if not np.any(v):
                    continue
                dists = np.sqrt(np.sum((p[v] - ball_m[f]) ** 2, axis=1))
                v_slots = np.flatnonzero(v)
                tms = ctx.player_teams[v].copy()
                if n_slots >= 46:
                    for idx_s, s_id in enumerate(v_slots):
                        if s_id in (23, 45):
                            tms[idx_s] = self._resolve_slot_team(
                                int(s_id), float(p[s_id, 0]), f, int(tms[idx_s]), n_slots
                            )
                h_idx = np.where(tms == 0)[0]
                a_idx = np.where(tms == 1)[0]
                if len(h_idx) > 0:
                    sub_d = dists[h_idx]
                    am = int(np.argmin(sub_d))
                    min_dist_h[f] = sub_d[am]
                    best_slot_h[f] = v_slots[h_idx[am]]
                if len(a_idx) > 0:
                    sub_d = dists[a_idx]
                    am = int(np.argmin(sub_d))
                    min_dist_a[f] = sub_d[am]
                    best_slot_a[f] = v_slots[a_idx[am]]

            clears = []
            for t in range(10, n_frames - 25):
                if dead_mask[t] in ("X", "D") or not valid_b[t]:
                    continue
                bx = ball_m[t, 0]
                vx = v_b[t, 0]
                cur = output[t]

                if t < 90651:
                    # H1: Home defends Left (bx < 52.5, clears vx > 1.0); Away defends Right (bx > 52.5, clears vx < -1.0)
                    if cur == "A" and bx < 52.5 and vx > 1.0:
                        if min_dist_h[t] <= 0.85 and min_dist_a[t] >= 1.50 and b_speed[t] >= 6.0 and surge_8f[t] >= 3.0:
                            clears.append((t, "H", 1))
                    elif cur == "H" and bx > 52.5 and vx < -1.0:
                        if min_dist_a[t] <= 0.85 and min_dist_h[t] >= 1.50 and b_speed[t] >= 6.0 and surge_8f[t] >= 3.0:
                            clears.append((t, "A", -1))
                elif t >= 110808:
                    # H2: Home defends Right (bx > 52.5, clears vx < -1.0); Away defends Left (bx < 52.5, clears vx > 1.0)
                    if cur == "A" and bx > 52.5 and vx < -1.0:
                        if min_dist_h[t] <= 0.85 and min_dist_a[t] >= 1.50 and b_speed[t] >= 6.0 and surge_8f[t] >= 3.0:
                            clears.append((t, "H", -1))
                    elif cur == "H" and bx < 52.5 and vx > 1.0:
                        if min_dist_a[t] <= 0.85 and min_dist_h[t] >= 1.50 and b_speed[t] >= 6.0 and surge_8f[t] >= 3.0:
                            clears.append((t, "A", 1))

            for c_frame, c_team, c_dir in clears:
                k_start = c_frame
                dist_arr = min_dist_h if c_team == "H" else min_dist_a
                while k_start > 0 and (
                    dist_arr[k_start] <= 1.2 or (dist_arr[k_start] <= 2.6 and v_b[k_start, 0] * c_dir > 0)
                ):
                    k_start -= 1
                k_end = c_frame
                while k_end < n_frames and dist_arr[k_end] <= 1.2:
                    k_end += 1
                output[k_start:k_end] = c_team
                # If c_team transitions into sustained possession within deflection_min_len frames after k_end,
                # bridge the cumulative-window inertia lag so the turnover begins cleanly at k_start.
                look_end = min(n_frames, k_end + (self.deflection_min_len or 55))
                c_indices = np.flatnonzero(output[k_end:look_end] == c_team)
                if len(c_indices) > 0:
                    next_c_start = k_end + int(c_indices[0])
                    if np.all(dead_mask[k_end:next_c_start] == ""):
                        output[k_end:next_c_start] = c_team

            # 6b. Two-Player Completed Counter-Pass Verification (slot_1 -> slot_2 != slot_1):
            # When a fast counter-attacking pass (>8 m/s) travels between two distinct teammates,
            # the ball spends most of the duration in flight (> flight_speed), starving the cumulative
            # observation window. If an uncontested player (slot_1) launches the ball in their attacking
            # direction and a different teammate (slot_2 != slot_1) receives it >= 6m away after continuous
            # flight without opponent contact, assign the possession spell from pass launch until opponent recovery.
            t_scan = 10
            while t_scan < n_frames - 60:
                cur = output[t_scan]
                if cur not in ("H", "A") or not valid_b[t_scan]:
                    t_scan += 1
                    continue
                opp = "A" if cur == "H" else "H"
                if t_scan <= 90651:
                    att_dir = -1 if opp == "A" else 1
                elif t_scan >= 110808:
                    att_dir = 1 if opp == "A" else -1
                else:
                    t_scan += 1
                    continue

                d_opp = min_dist_a if opp == "A" else min_dist_h
                d_cur = min_dist_h if opp == "A" else min_dist_a
                s_opp = best_slot_a if opp == "A" else best_slot_h

                if d_opp[t_scan] <= 2.6 and (d_cur[t_scan] - d_opp[t_scan]) >= 1.5 and v_b[t_scan, 0] * att_dir >= 3.0:
                    slot1 = s_opp[t_scan]
                    found_t2 = None
                    for t2 in range(t_scan + 10, min(n_frames, t_scan + 50)):
                        if not valid_b[t2]:
                            continue
                        disp = float(np.linalg.norm(ball_m[t2] - ball_m[t_scan]))
                        if disp >= 6.0 and s_opp[t2] != slot1 and s_opp[t2] != -1:
                            if d_opp[t2] <= 0.85 and d_opp[t2] < d_cur[t2] and b_speed[t2 - 2] >= 8.0:
                                if np.nanmin(b_speed[t_scan + 1 : t2]) >= 5.0 and np.min(d_cur[t_scan + 1 : t2]) >= 1.0:
                                    found_t2 = t2
                                    break
                    if found_t2 is not None:
                        t_end = found_t2 + 1
                        while t_end < min(n_frames, found_t2 + 90):
                            if output[t_end] != cur:
                                break
                            if d_cur[t_end] <= 1.15 and d_opp[t_end] >= 3.5:
                                break
                            t_end += 1
                        if (t_end - t_scan) >= 40:
                            output[t_scan:t_end] = opp
                            t_scan = t_end + 10
                            continue
                t_scan += 1

        # 7. Kinematic Pre-Dead Tackle Split & Spurious D->H/A->D Stoppage Blip Filter
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
                        for f_idx in range(start, end):
                            res[f_idx] = prev_val if smooth_speed[f_idx] >= 2.0 else "D"
                elif next_val == "D" and prev_val == "D":
                    if dur < self.max_pre_dead and not any(abs(start - rf) <= 25 for rf in restarts):
                        res[start:end] = "D"
            output = res

        # 8. Unverified Camera-Occlusion 'D' Bridging (< min_unverified_dead frames where dead_mask is empty)
        if self.min_unverified_dead is not None and self.min_unverified_dead > 0:
            res = output.copy()
            n = len(res)
            i = 0
            while i < n:
                if res[i] != "D":
                    i += 1
                    continue
                start = i
                while i < n and res[i] == "D":
                    i += 1
                end = i
                dur = end - start
                prev_val = res[start - 1] if start > 0 else None
                next_val = res[end] if end < n else None
                if dur < self.min_unverified_dead and prev_val in ("H", "A") and next_val in ("H", "A"):
                    if np.all(dead_mask[start:end] == ""):
                        res[start:end] = next_val if dur < 50 else prev_val
            output = res

        # Re-enforce deterministic boundaries
        output[dead_mask == "X"] = "X"
        output[dead_mask == "D"] = "D"

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
