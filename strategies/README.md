# Possession Strategy Registry & Scientific Benchmarking

This directory contains modular, independent possession inference strategies.
Each strategy implements the `BaseStrategy` interface (`predict(TrackingContext) -> np.ndarray[labels]`) and can be tested and benchmarked independently.

---

## 1. Registered Strategies

| Strategy | Type | Core Hypothesis | Key Hyperparameters |
|---|---|---|---|
| **`football_engine`** | **Production Champion** | Decoupled 7-phase physical state machine combining GK optical slot disambiguation (`s23` & `s45`), Smart Tagging `GOALS` build-up preservation, consecutive `SET PIECES` bridge recovery, `Throw-in` post-throw verification, turnover hysteresis barrier ($\delta=11$), dynamic flight gating ($r=1.5\text{m}, v>8.0\text{m/s}$), half-symmetric kickoff arrival, 4-way symmetric clearances with velocity-apex extension, 2-player completed counter-pass verification, camera-occlusion bridging, IFAB Law 13 stationary ball free-kick gating, corner-kick deceleration envelopes, and biomechanical micro-flicker filtering. Achieves **`spellF1 = 0.9375`** (uniform across all five IoU thresholds `0.3..0.7`, `15/15` precision) and **`macroF1 = 0.9732`** (+285% over baseline floor!). | `w_past=65`, `w_future=15`, `turnover_barrier=11`, `control_radius=3.0`, `deflection_min_len=55`, `max_pre_dead=90`, `min_unverified_dead=120`, `min_flicker_len=15`, `min_dead_flicker_len=40` |
| **`fsm_hysteresis`** | **Inertia-Hysteresis** | Overcomes frame-by-frame turnover jitter by requiring cumulative opponent evidence to exceed possessor evidence by a barrier $\delta$: $E_{opp} > E_{poss} + \delta$. | `window=60`, `turnover_barrier=15` |
| **`fsm_advanced`** | **Kinematic FSM** | Incorporates collective team deceleration ($v < 1.6\text{ m/s}$) and prolonged missing ball to detect dead-ball stoppages. | `decel_threshold=1.6`, `dead_window=30` |
| **`fsm_lookahead`** | **Primary (FSM)** | Football possession is an inertia state. Looking ahead $1.0\text{s}$ ($25\text{ frames}$) filters out deflections and prevents false splits, maximizing `spellF1`. | `lookahead_window=25`, `min_turnover_frames=8`, `control_radius=2.0` |
| **`ablation_no_lookahead`** | **Ablation** | Tests what happens when lookahead is removed and turnovers are committed on first opponent contact. | `lookahead_window=0` |
| **`ablation_no_deadball`** | **Ablation** | Tests what happens when Smart Tagging set-piece stoppage priors are ignored. | `restarts=kickoffs_only` |
| **`hmm_viterbi`** | **Probabilistic** | Models football inertia via state transitions in log-probability space ($P(S_t = S_{t-1}) \approx 0.98$) and finds global path via Viterbi. | `self_trans_prob=0.98`, `turnover_penalty=1e-4` |
| **`baseline_smooth50`** | **Floor Baseline** | Nearest player to ball + centered 50-frame majority vote. Official floor to beat ($0.2433$). | `window_half_width=50` |
| **`baseline_smooth25`** | **Baseline** | Fast smoothing (+/- 1s). Tends to under-smooth on full match. | `window_half_width=25` |
| **`baseline_smooth125`** | **Baseline** | Heavy smoothing (+/- 5s). Overfits public 5-minute GT. | `window_half_width=125` |
| **`baseline_raw`** | **Baseline** | Unsmoothed nearest player. Demonstrates extreme fragmentation. | `window_half_width=0` |

---

## 2. Running & Testing Strategies

### A. Synthetic Unit Tests (No match data needed)
Verify that all strategies execute cleanly and pass edge-case transition tests:
```powershell
.\.venv\Scripts\python.exe run_experiment.py --test-all
```

### B. List Available Strategies
```powershell
.\.venv\Scripts\python.exe run_experiment.py --list
```

### C. Run an Experiment with Auto-Logging
Runs the strategy, produces a validated CSV, scores it on ground truth, and appends the result to `experiments/EXPERIMENT_LOG.md` and `experiments/history.jsonl`:
```powershell
.\.venv\Scripts\python.exe run_experiment.py --strategy fsm_lookahead --notes "Baseline FSM with 25f lookahead"
```

### D. Benchmark All Strategies Side-by-Side
```powershell
.\.venv\Scripts\python.exe run_experiment.py --strategy all
```

---

## 3. How to Add a New Strategy

1. Create `strategies/my_new_strategy.py`:
   ```python
   from strategies.base import BaseStrategy, TrackingContext
   import numpy as np

   class MyNewStrategy(BaseStrategy):
       def __init__(self, my_param=1.5, name="my_strategy"):
           super().__init__(name=name, description="...", my_param=my_param)
           self.my_param = my_param

       def predict(self, ctx: TrackingContext) -> np.ndarray:
           # Output exactly ctx.n_frames labels ('H', 'A', 'D', 'X')
           ...
           return labels

       def test_synthetic(self) -> bool:
           # Unit test with mock data
           return True
   ```
2. Register it in `strategies/__init__.py`:
   ```python
   from strategies.my_new_strategy import MyNewStrategy
   STRATEGY_REGISTRY["my_strategy"] = MyNewStrategy
   ```
3. Run `python run_experiment.py --test-all` to verify, then benchmark!
