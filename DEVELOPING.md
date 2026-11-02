# Developer & Contributor Guide — More Than A Hack 2027

Welcome to the team! This repository contains the ball possession inference pipeline for the **More Than A Hack 2027** competition (Phase 1: Ball Possession), organized by Metrica Sports, FC Barcelona, and Mobile World Capital Barcelona.

This guide walks you through setting up your environment, understanding the architecture, testing strategies, and contributing new models.

> [!IMPORTANT]
> **Every change needs an approved OpenSpec change before implementation** — no exceptions for
> small fixes, docs, tests, dependencies or CI. Read [`AGENTS.md` §0](AGENTS.md) (policy) and
> [`docs/OPEN_SPEC_WORKFLOW.md`](docs/OPEN_SPEC_WORKFLOW.md) (procedure) first. The CI check
> `openspec-governance` rejects pull requests that do not follow it.

---

## 1. The Challenge at a Glance

- **Goal**: Predict who has the ball for every frame of the match (Barcelona vs Athletic Club).
- **Target Output**: A CSV with `frame,label` containing **exactly 199,319 rows** (frames `0` to `199318`).
- **Four Labels**:
  - `H`: FC Barcelona (Home) in controlled possession.
  - `A`: Athletic Club (Away) in controlled possession.
  - `D`: Dead ball (out of play / stoppage).
  - `X`: No answer / abstention (used for ungraded frames and severe occlusions).
- **Primary Metric**: **`spellF1`** — Temporal IoU ($[0.3..0.7]$) matching of whole possession spells.
  - *Baseline floor to beat*: `baseline_smooth50` achieves full-match `spellF1 = 0.2433`.
  - *Tie-breaker*: Frame-by-frame `macroF1` (baseline $\approx 0.67$).

---

## 2. Quickstart & Environment Setup

### Prerequisites
- Python 3.11+ (Python 3.13 supported)
- Git

### Setup Virtual Environment
```bash
# Clone the repository
git clone <repo-url>
cd more-than-a-hack-2027

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install core dependencies
pip install -r requirements.txt
```

### Install Pre-commit Hooks
Pre-commit checks run automatically on every `git commit` to prevent broken strategies or malformed submissions from landing in git:
```bash
pip install pre-commit
pre-commit install
```
*(A standalone git pre-commit hook is also pre-installed in `.git/hooks/pre-commit` to verify code even without global tools).*

---

## 3. Core Architectural Principle: The Football State Machine

In football, **possession is an inertia-driven state**, not an isolated per-frame vote:
- The ball is missing on **41% of graded frames**.
- Passes in flight, aerial duels, and momentary deflections happen constantly.
- **Inertia**: Once Team H has possession, Team H *retains* possession across passes, loose balls, and occlusions until the opponent *establishes controlled possession* or play stops (`D`).
- **Turnover Guard with Lookahead**: Opponent contact triggers a forward verification window ($+25\text{ frames} = 1.0\text{ s}$). If the ball rebounds back to the original team, it was a deflection—possession is preserved.
- **Why this optimizes `spellF1`**: Temporal IoU penalizes false splits severely. Preserving whole possession objects directly maximizes `spellF1`.

---

## 4. Strategy Architecture: Pluggable & Independent

All models reside in [`strategies/`](strategies/) and inherit from `BaseStrategy`:

```
strategies/
├── base.py                 # Abstract BaseStrategy & TrackingContext interface
├── football_engine.py      # Production Champion: GK Slot Disambiguation, 4-Way Symmetric Clearances, 2-Player Pass Verification, Set-Piece/Goals/Restart Gating & Occlusion Bridging (spellF1=0.9375, macroF1=0.9730)
├── fsm_hysteresis.py       # Inertia-Hysteresis turnover barrier benchmark
├── fsm_advanced.py         # Deceleration + missing ball kinematic state machine
├── fsm_lookahead.py        # Primary: Football State Machine with lookahead
├── fsm_ablation.py         # Ablation studies (no-lookahead, no-deadball priors)
├── hmm_viterbi.py          # Probabilistic HMM with Viterbi sequence decoding
├── baseline_window.py      # Reference nearest-player + majority vote baselines
└── __init__.py             # Registry (STRATEGY_REGISTRY)
```

Each strategy implements two methods:
1. `predict(ctx: TrackingContext) -> np.ndarray`: Produces the 199,319 frame labels.
2. `test_synthetic() -> bool`: Standalone unit test on synthetic match sequences (no match data needed).

---

## 5. Testing & Verification

### Run Synthetic Unit Tests Across All Strategies
Verify all strategies against edge cases (deflections, turnovers, stoppages) in 2 seconds:
```bash
python run_experiment.py --test-all
```

### List Registered Strategies
```bash
python run_experiment.py --list
```

### Check Data Asset Status
```bash
python tools/data_status.py
```

---

## 6. How to Add a New Strategy in 3 Steps

### Step 1: Create your strategy file in `strategies/my_strategy.py`
```python
from strategies.base import BaseStrategy, TrackingContext
import numpy as np

class MyStrategy(BaseStrategy):
    def __init__(self, my_param: float = 1.5, name: str = "my_strategy"):
        super().__init__(name=name, description="My custom possession strategy", my_param=my_param)
        self.my_param = my_param

    def predict(self, ctx: TrackingContext) -> np.ndarray:
        # ctx provides: ctx.n_frames (199319), ctx.ball_coords, ctx.player_coords,
        # ctx.player_teams, ctx.dead_ball_mask, ctx.restarts, ctx.pitch_dim
        labels = np.full(ctx.n_frames, "D", dtype="<U1")
        # Your custom logic here...
        labels[ctx.dead_ball_mask == "X"] = "X"
        return labels

    def test_synthetic(self) -> bool:
        # Quick unit test verifying edge cases
        return True
```

### Step 2: Register it in `strategies/__init__.py`
```python
from strategies.my_strategy import MyStrategy

STRATEGY_REGISTRY["my_strategy"] = MyStrategy
```

### Step 3: Test and Benchmark!
```bash
# Verify synthetic tests pass
python run_experiment.py --test-all

# Run experiment and score (auto-logs to experiments/EXPERIMENT_LOG.md)
python run_experiment.py --strategy my_strategy --notes "Testing my new strategy"
```

---

## 7. Experiment Logging & Scoreboard

Every strategy run with `run_experiment.py` automatically:
1. Generates the submission CSV in `evaluation/results/<strategy_name>.csv`.
2. Validates the submission format (`validate_submission.py`).
3. Evaluates against public ground truth (`agent_eval.py`).
4. Logs parameters and results to:
   - `experiments/EXPERIMENT_LOG.md` (human-readable scoreboard table)
   - `experiments/history.jsonl` (machine-readable structured log)

---

## 8. CI/CD & Automated Quality Enforcement

- **Pre-commit**: Blocks commits locally if any strategy synthetic test fails or if baseline submissions are invalidated.
- **GitHub Actions Pipeline (`.github/workflows/ci.yml`)**:
  - Triggers on every pull request and push to `main`.
  - Runs on **Ubuntu** and **Windows** across **Python 3.11 & 3.13**.
  - Runs all strategy synthetic tests.
  - Runs full baseline evaluation and format verification.
  - Verifies that no restricted/gated data files are accidentally checked into git.

---

## 9. Critical Rule: The 5-Minute Public Ground Truth Trap

> [!WARNING]
> The public ground truth (`evaluation/gt/BAR-ATH_possession_gt_public.csv`) covers **only the first 5 minutes (17 possessions)**.
> - **DO NOT hyperparameter-tune or train models against the public 5 minutes.**
> - `baseline_smooth125` scored `0.4242` on the 5-minute GT, but collapsed to `0.2242` on the full match.
> - `baseline_smooth50` scored `0.3256` on the 5-minute GT, but won on the full match with `0.2433`.
> - Use the public GT **strictly as a sanity check** to confirm that pipelines run without crashing and boundaries align.

---

## 10. Submission Checklist Before Deadline

Before uploading to the official Google Form:
1. **Validate Format**:
   ```bash
   python evaluation/validate_submission.py evaluation/results/<team_name>.csv
   ```
2. **Confirm Exact Rows**: Exactly `199,319` rows with header `frame,label`.
3. **No Blanks**: Use `X` where abstaining (e.g. pre-match, halftime, post-match).
4. **Deliverables Ready**:
   - Possession file: `<team_name>.csv`
   - Short technical document: `<team_name>.pdf` (or `.md`)
   - Public code repository URL (ensure clean git tree without gated match data).
