"""Strategy: Football State Machine with Bidirectional Lookahead (Primary Strategy).

Enforces:
1. Possession Inertia: stays in current state across passes, loose balls, and occlusions.
2. Turnover Guard with Lookahead: an opponent contact triggers a forward window inspection
   (default 25 frames / 1.0s). If the ball returns to the original team, it is treated as a
   deflection/rebound and possession is retained.
3. Clean Stoppage & Restart integration: respects dead-ball intervals ('D') and transitions to restarting teams.
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext
from pipeline.ball_reconstruction import reconstruct_ball_trajectory
from pipeline.evidence import compute_frame_control_evidence
from pipeline.state_machine import FootballStateMachine


class FSMLookaheadStrategy(BaseStrategy):
    """Football State Machine with lookahead turnover verification."""

    def __init__(
        self,
        lookahead_window: int = 25,
        min_turnover_frames: int = 8,
        max_turnover_rebound_gap: int = 15,
        control_radius: float = 2.0,
        max_ball_interp_gap: int = 20,
        name: str = "fsm_lookahead",
    ):
        super().__init__(
            name=name,
            description="Football State Machine with inertia and forward lookahead turnover verification",
            lookahead_window=lookahead_window,
            min_turnover_frames=min_turnover_frames,
            max_turnover_rebound_gap=max_turnover_rebound_gap,
            control_radius=control_radius,
            max_ball_interp_gap=max_ball_interp_gap,
        )
        self.lookahead_window = lookahead_window
        self.min_turnover_frames = min_turnover_frames
        self.max_turnover_rebound_gap = max_turnover_rebound_gap
        self.control_radius = control_radius
        self.max_ball_interp_gap = max_ball_interp_gap

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames

        # 1. Reconstruct missing ball coordinates for short gaps
        interp_ball, _ = reconstruct_ball_trajectory(
            ctx.ball_coords, max_gap_frames=self.max_ball_interp_gap
        )

        # 2. Extract control evidence for each frame
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

        # 3. Execute state machine with lookahead
        fsm = FootballStateMachine(
            lookahead_window=self.lookahead_window,
            min_turnover_frames=self.min_turnover_frames,
            max_turnover_rebound_gap=self.max_turnover_rebound_gap,
        )
        final_labels = fsm.run(
            n_frames=n_frames,
            nearest_teams=nearest_teams,
            has_controls=has_controls,
            dists_h=dists_h,
            dists_a=dists_a,
            dead_ball_mask=ctx.dead_ball_mask,
            restarts=ctx.restarts,
        )
        return final_labels

    def test_synthetic(self) -> bool:
        n = 200
        # Center of pitch
        ball = np.ones((n, 2), dtype=np.float32) * 0.5
        players = np.ones((n, 2, 2), dtype=np.float32) * 0.6  # Default Away far
        players[:, 0, :] = 0.505  # Home in tight control (~0.5m away)
        teams = np.array([0, 1], dtype=np.int8)
        mask = np.full(n, "", dtype="<U1")
        mask[:20] = "X"
        mask[180:] = "X"

        # Opponent touch deflection at frame 60 (3 frames only)
        players[60:63, 1, :] = 0.502
        players[60:63, 0, :] = 0.550

        # Opponent sustained possession at frames 100..150
        players[100:150, 1, :] = 0.502
        players[100:150, 0, :] = 0.580

        ctx = TrackingContext(
            n_frames=n,
            ball_coords=ball,
            player_coords=players,
            player_teams=teams,
            dead_ball_mask=mask,
            restarts={20: "H"},
        )
        res = self.predict(ctx)

        # Deflection at 60 must be absorbed (stays H)
        assert res[60] == "H" and res[61] == "H" and res[62] == "H", "Deflection must be absorbed by lookahead"
        # Sustained turnover at 100 must transition to A
        assert res[115] == "A" and res[140] == "A", "Sustained challenge must transition to A"
        return True
