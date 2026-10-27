"""Strategy: Nearest Player + Centered Majority-Vote Window (Baseline Reference).

This is an independent implementation of the official baseline approach.
Assigns ball to nearest tracked player (or D if ball is missing), then
applies a centered majority-vote smoothing window.
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext


class BaselineWindowStrategy(BaseStrategy):
    """Nearest player with rolling majority-vote window."""

    def __init__(self, window_half_width: int = 50, name: str = None):
        name = name or f"baseline_smooth{window_half_width}" if window_half_width > 0 else "baseline_raw"
        super().__init__(
            name=name,
            description=f"Nearest player to ball with centered majority vote window of +/-{window_half_width} frames",
            window_half_width=window_half_width,
        )
        self.w = window_half_width

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames
        n_slots = len(ctx.player_teams)
        raw_labels = np.full(n_frames, "D", dtype="<U1")

        # Compute metric scale
        scale = np.array([ctx.pitch_dim[0], ctx.pitch_dim[1]], dtype=np.float32)

        for f in range(n_frames):
            # Respect ungraded frames
            if ctx.dead_ball_mask[f] == "X":
                raw_labels[f] = "X"
                continue

            # Respect pre-kickoff D
            if ctx.dead_ball_mask[f] == "D":
                raw_labels[f] = "D"
                continue

            ball = ctx.ball_coords[f]
            if np.isnan(ball[0]) or np.isnan(ball[1]):
                raw_labels[f] = "D"
                continue

            ball_m = ball * scale
            players_m = ctx.player_coords[f] * scale
            valid_p = ~np.isnan(players_m[:, 0]) & ~np.isnan(players_m[:, 1])

            if not np.any(valid_p):
                raw_labels[f] = "D"
                continue

            diffs = players_m[valid_p] - ball_m
            dists = np.sum(diffs**2, axis=1)
            teams = ctx.player_teams[valid_p]
            nearest_team = teams[np.argmin(dists)]
            raw_labels[f] = "H" if nearest_team == 0 else "A"

        # Apply centered majority vote smoothing if w > 0
        if self.w <= 0:
            return raw_labels

        smoothed = raw_labels.copy()
        label_map = {"H": 0, "A": 1, "D": 2, "X": 3}
        inv_map = {0: "H", 1: "A", 2: "D", 3: "X"}
        codes = np.array([label_map[x] for x in raw_labels], dtype=np.int8)

        # Smooth only over graded frames
        for f in range(n_frames):
            if ctx.dead_ball_mask[f] == "X":
                continue
            start = max(0, f - self.w)
            end = min(n_frames, f + self.w + 1)
            window = codes[start:end]
            # Exclude X from vote
            valid_window = window[window != 3]
            if len(valid_window) > 0:
                counts = np.bincount(valid_window, minlength=3)
                smoothed[f] = inv_map[np.argmax(counts)]

        # Re-enforce deterministic boundaries
        smoothed[ctx.dead_ball_mask == "X"] = "X"
        smoothed[ctx.dead_ball_mask == "D"] = "D"
        return smoothed

    def test_synthetic(self) -> bool:
        n = 100
        ball = np.zeros((n, 2))
        players = np.ones((n, 2, 2)) * 10
        players[:, 0, :] = 0.5  # Home closer
        teams = np.array([0, 1])
        mask = np.full(n, "", dtype="<U1")
        mask[:10] = "X"
        mask[80:] = "D"

        ctx = TrackingContext(n_frames=n, ball_coords=ball, player_coords=players, player_teams=teams, dead_ball_mask=mask)
        res = self.predict(ctx)
        assert res[0] == "X"
        assert res[85] == "D"
        assert res[50] == "H"
        return True
