"""Football State Machine with Bidirectional Lookahead Turnover Verification.

Optimizes directly for spellF1:
1. Enforces Possession Inertia: stays in current state across passes, loose balls,
   and occlusions.
2. Turnover Guard with Lookahead: an opponent contact only triggers a transition
   if the opponent maintains established control in the subsequent window (15-30 frames).
   Brief deflections and 50/50 rebounds are absorbed without splitting the spell.
3. Clean Stoppage & Restart integration: respects dead-ball intervals ('D') and
   transitions to restarting teams.
"""

import numpy as np


class FootballStateMachine:
    """Offline Finite State Machine for football ball possession inference."""

    def __init__(
        self,
        lookahead_window=25,
        min_turnover_frames=8,
        max_turnover_rebound_gap=15,
    ):
        """
        Args:
            lookahead_window: Number of forward frames to inspect upon opponent contact (25 frames = 1.0s)
            min_turnover_frames: Minimum frames opponent must control the ball in lookahead window
            max_turnover_rebound_gap: Max gap allowed before original team recovery classifies it as a deflection
        """
        self.lookahead_window = lookahead_window
        self.min_turnover_frames = min_turnover_frames
        self.max_turnover_rebound_gap = max_turnover_rebound_gap

    def run(
        self,
        n_frames,
        nearest_teams,
        has_controls,
        dists_h,
        dists_a,
        dead_ball_mask,
        restarts=None,
    ):
        """Execute state machine over the match frames.

        Args:
            n_frames: Total number of frames (199,319)
            nearest_teams: List/array of 'H', 'A', or None per frame
            has_controls: Boolean array of whether nearest player has tight control
            dists_h: Array of float distances (meters) to Home player
            dists_a: Array of float distances (meters) to Away player
            dead_ball_mask: Array of shape (n_frames,) with 'X', 'D', or ''
            restarts: Dict of {frame_idx: 'H' or 'A'} specifying restart kickoff/set-piece possession

        Returns:
            np.ndarray of shape (n_frames,) containing final labels ('H', 'A', 'D', 'X')
        """
        restarts = restarts or {}
        output = np.full(n_frames, "X", dtype="<U1")
        current_state = None  # 'H', 'A', or 'D'

        t = 0
        while t < n_frames:
            # 1. Deterministic Ungraded Check
            if dead_ball_mask[t] == "X":
                output[t] = "X"
                current_state = None
                t += 1
                continue

            # 2. Deterministic Dead Ball Stoppage Check
            if dead_ball_mask[t] == "D":
                output[t] = "D"
                current_state = "D"
                t += 1
                continue

            # 3. Check explicit restart anchors at frame t
            if t in restarts:
                current_state = restarts[t]
                output[t] = current_state
                t += 1
                continue

            # 4. Handle State Transitions
            if current_state is None or current_state == "D":
                # Restart from dead ball / start of play
                # First team to establish control or proximity gets possession
                if nearest_teams[t] in ("H", "A") and has_controls[t]:
                    current_state = nearest_teams[t]
                elif nearest_teams[t] in ("H", "A") and (dists_h[t] < 3.0 or dists_a[t] < 3.0):
                    current_state = nearest_teams[t]
                else:
                    # Stoppage continues until ball is put into play
                    current_state = "D"
                output[t] = current_state
                t += 1
                continue

            # 5. In-Play Possession: Current state is 'H' or 'A'
            opponent = "A" if current_state == "H" else "H"
            nearest = nearest_teams[t]
            in_control = has_controls[t]

            # Possession Inertia: Default is to maintain current team possession
            if nearest != opponent or not in_control:
                # Same team in possession, ball in flight, loose ball, or occluded
                output[t] = current_state
                t += 1
                continue

            # 6. Candidate Turnover: Opponent is nearest and in control at frame t
            # If lookahead is disabled (ablation mode), switch immediately
            if self.lookahead_window <= 0:
                current_state = opponent
                output[t] = current_state
                t += 1
                continue

            # Trigger Bidirectional Lookahead Verification:
            # Inspect future window [t + 1 .. min(t + W, n_frames)]
            lookahead_end = min(t + self.lookahead_window, n_frames)
            future_nearest = nearest_teams[t : lookahead_end]
            future_dead = dead_ball_mask[t : lookahead_end]

            # If play stops in lookahead, let stoppage handle it naturally
            if np.any(future_dead == "D"):
                output[t] = current_state
                t += 1
                continue

            # Count evidence in lookahead
            opp_count = np.sum(future_nearest == opponent)
            orig_count = np.sum(future_nearest == current_state)

            # Check for immediate rebound to original team (deflection)
            # Find first frame where original team regains proximity
            orig_indices = np.flatnonzero(future_nearest == current_state)
            rebounded_quickly = (
                len(orig_indices) > 0 and orig_indices[0] <= self.max_turnover_rebound_gap
            )

            if rebounded_quickly and orig_count >= opp_count:
                # DEFLECTION / REBOUND: Opponent touched ball but did not gain control
                # Possession stays with original team throughout
                output[t] = current_state
                t += 1
            elif opp_count >= self.min_turnover_frames and opp_count > orig_count:
                # VERIFIED TURNOVER: Opponent established control
                current_state = opponent
                output[t] = current_state
                t += 1
            else:
                # Unclear / contested contest: Possession inertia holds
                output[t] = current_state
                t += 1

        return output
