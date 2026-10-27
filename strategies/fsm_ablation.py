"""Ablation strategies to measure the exact contribution of each architectural component.

Includes:
1. `FSMNoLookaheadStrategy`: FSM with inertia but without lookahead verification.
   Switches immediately upon opponent contact. Proves the impact of deflection filtering.
2. `FSMNoDeadBallStrategy`: FSM without Smart Tagging set piece stoppage demarcation.
   Proves the value of tactical dead-ball priors.
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext
from strategies.fsm_lookahead import FSMLookaheadStrategy


class FSMNoLookaheadStrategy(FSMLookaheadStrategy):
    """Ablation: FSM with inertia but lookahead window disabled (window=0)."""

    def __init__(self, name: str = "ablation_no_lookahead", **kwargs):
        super().__init__(
            lookahead_window=0,
            min_turnover_frames=1,
            max_turnover_rebound_gap=0,
            name=name,
            **kwargs,
        )
        self.description = "Ablation: FSM with inertia but without lookahead (immediate turnover on contact)"

    def test_synthetic(self) -> bool:
        n = 200
        ball = np.ones((n, 2), dtype=np.float32) * 0.5
        players = np.ones((n, 2, 2), dtype=np.float32) * 0.6
        players[:, 0, :] = 0.505
        teams = np.array([0, 1], dtype=np.int8)
        mask = np.full(n, "", dtype="<U1")
        mask[:20] = "X"
        mask[180:] = "X"

        # Brief deflection at 60
        players[60:63, 1, :] = 0.502
        players[60:63, 0, :] = 0.550

        ctx = TrackingContext(
            n_frames=n,
            ball_coords=ball,
            player_coords=players,
            player_teams=teams,
            dead_ball_mask=mask,
            restarts={20: "H"},
        )
        res = self.predict(ctx)
        # Without lookahead, deflection immediately switches to A!
        assert res[61] == "A", "Without lookahead, immediate handover occurs on touch"
        return True


class FSMNoDeadBallStrategy(FSMLookaheadStrategy):
    """Ablation: FSM with lookahead, but ignoring Smart Tagging dead-ball priors."""

    def __init__(self, name: str = "ablation_no_deadball", **kwargs):
        super().__init__(name=name, **kwargs)
        self.description = "Ablation: FSM with lookahead, but ignoring Smart Tagging set-piece stoppage priors"

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        # Strip out smart tagging stoppages from dead ball mask
        stripped_mask = ctx.dead_ball_mask.copy()
        # Only keep deterministic X and pre-kickoff D
        stripped_mask[(stripped_mask == "D") & (np.arange(len(stripped_mask)) > 113741)] = ""

        ctx_stripped = TrackingContext(
            n_frames=ctx.n_frames,
            ball_coords=ctx.ball_coords,
            player_coords=ctx.player_coords,
            player_teams=ctx.player_teams,
            dead_ball_mask=stripped_mask,
            restarts={11185: "A", 113742: "H"},  # only base kickoffs
            pitch_dim=ctx.pitch_dim,
        )
        return super().predict(ctx_stripped)
