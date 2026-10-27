"""Strategy: Hidden Markov Model (HMM) with Viterbi State Decoding.

Probabilistic formulation:
- Hidden states: {0: 'H', 1: 'A', 2: 'D'}
- Transition matrix encodes football inertia:
  * High self-transition probabilities (P(S_t = S_{t-1}) ~ 0.98)
  * Heavy penalty on direct H <-> A handovers without deceleration or contested phase
- Emissions derived from relative player-ball distance ratios and dead-ball mask
- Global Viterbi algorithm finds the optimal global state trajectory
"""

import numpy as np
from strategies.base import BaseStrategy, TrackingContext
from pipeline.ball_reconstruction import reconstruct_ball_trajectory
from pipeline.evidence import compute_frame_control_evidence


class HMMViterbiStrategy(BaseStrategy):
    """Hidden Markov Model for global sequence decoding."""

    def __init__(
        self,
        self_trans_prob: float = 0.98,
        dead_self_prob: float = 0.95,
        turnover_penalty: float = 1e-4,
        name: str = "hmm_viterbi",
    ):
        super().__init__(
            name=name,
            description="Probabilistic HMM with high inertia and global Viterbi sequence decoding",
            self_trans_prob=self_trans_prob,
            dead_self_prob=dead_self_prob,
            turnover_penalty=turnover_penalty,
        )
        self.self_trans_prob = self_trans_prob
        self.dead_self_prob = dead_self_prob
        self.turnover_penalty = turnover_penalty

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        n_frames = ctx.n_frames
        states = ["H", "A", "D"]
        n_states = len(states)

        # 1. Transition Matrix A (log space)
        # S0=H, S1=A, S2=D
        A = np.zeros((n_states, n_states), dtype=np.float64)
        A[0, 0] = self.self_trans_prob
        A[0, 1] = self.turnover_penalty
        A[0, 2] = 1.0 - A[0, 0] - A[0, 1]

        A[1, 1] = self.self_trans_prob
        A[1, 0] = self.turnover_penalty
        A[1, 2] = 1.0 - A[1, 1] - A[1, 0]

        A[2, 2] = self.dead_self_prob
        A[2, 0] = (1.0 - self.dead_self_prob) / 2.0
        A[2, 1] = (1.0 - self.dead_self_prob) / 2.0

        log_A = np.log(np.maximum(A, 1e-12))

        # 2. Compute Emissions (log space)
        interp_ball, _ = reconstruct_ball_trajectory(ctx.ball_coords, max_gap_frames=20)
        log_emissions = np.zeros((n_frames, n_states), dtype=np.float64)

        for f in range(n_frames):
            if ctx.dead_ball_mask[f] == "D":
                log_emissions[f] = [-10.0, -10.0, 0.0]
                continue
            if ctx.dead_ball_mask[f] == "X":
                log_emissions[f] = [0.0, 0.0, 0.0]
                continue

            ev = compute_frame_control_evidence(
                interp_ball[f],
                ctx.player_coords[f],
                ctx.player_teams,
                pitch_dim=ctx.pitch_dim,
            )
            dH = min(ev["dist_H"], 20.0)
            dA = min(ev["dist_A"], 20.0)

            # Softmax-style likelihood based on inverse distance
            score_H = -dH / 2.0
            score_A = -dA / 2.0
            score_D = -4.0 if (dH < 3.0 or dA < 3.0) else -1.0

            log_emissions[f, 0] = score_H
            log_emissions[f, 1] = score_A
            log_emissions[f, 2] = score_D

        # 3. Viterbi Decoding in Log Space
        viterbi = np.zeros((n_frames, n_states), dtype=np.float64)
        backpointer = np.zeros((n_frames, n_states), dtype=np.int32)

        # Initial state: equal prior or D
        viterbi[0] = log_emissions[0]

        for t in range(1, n_frames):
            # Shape: (from_state, to_state) = viterbi[t-1, :] + log_A[:, :]
            trans_scores = viterbi[t - 1, :, None] + log_A
            best_prev = np.argmax(trans_scores, axis=0)
            viterbi[t] = trans_scores[best_prev, np.arange(n_states)] + log_emissions[t]
            backpointer[t] = best_prev

        # Backtrack
        best_path = np.zeros(n_frames, dtype=np.int32)
        best_path[-1] = np.argmax(viterbi[-1])

        for t in range(n_frames - 2, -1, -1):
            best_path[t] = backpointer[t + 1, best_path[t + 1]]

        output = np.array([states[idx] for idx in best_path], dtype="<U1")
        output[ctx.dead_ball_mask == "X"] = "X"
        output[ctx.dead_ball_mask == "D"] = "D"
        return output

    def test_synthetic(self) -> bool:
        n = 100
        ball = np.ones((n, 2), dtype=np.float32) * 0.5
        players = np.ones((n, 2, 2), dtype=np.float32) * 0.6
        players[:, 0, :] = 0.505  # Home player 0.5m from ball
        teams = np.array([0, 1], dtype=np.int8)
        mask = np.full(n, "", dtype="<U1")
        mask[:10] = "X"
        mask[80:] = "D"

        ctx = TrackingContext(
            n_frames=n,
            ball_coords=ball,
            player_coords=players,
            player_teams=teams,
            dead_ball_mask=mask,
        )
        res = self.predict(ctx)
        assert res[0] == "X"
        assert res[85] == "D"
        assert res[40] == "H"
        return True
