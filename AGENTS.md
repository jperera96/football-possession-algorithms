# More Than A Hack 2027 — Phase 1: Ball Possession
## AI Agent Operational Guide & Workspace Rules

This repository is for the **More Than A Hack 2027** competition (Phase 1: Ball Possession), organized by Metrica Sports, FC Barcelona, and Mobile World Capital Barcelona.

---

### 1. Match & Goal Definition
- **Match**: FC Barcelona vs Athletic Club (`BAR-ATH`), LaLiga 2024-25 Matchday 2.
- **Teams**: Home (`H`) = FC Barcelona, Away (`A`) = Athletic Club.
- **Contract**: Produce a CSV with header `frame,label` for every tactical video frame (exactly **199,319** rows, frames `0` to `199318`).
- **Four Labels**:
  - `H`: Home team in controlled possession (ball in play).
  - `A`: Away team in controlled possession (ball in play).
  - `D`: Dead ball (ball out of play / stoppage).
  - `X`: No answer / abstention (used for ungraded frames and uncertain periods).

---

### 2. Graded vs Ungraded Frames
| Interval | Video Frames | Status | Ground Truth Note |
|---|---|---|---|
| Pre-match | `0 .. 11184` | Ungraded | Ungraded, use `X` |
| **1st Half** | **`11185 .. 90651`** (79,467 frames) | **Graded** | 1st half kickoff is frame 11,185 |
| Halftime | `90652 .. 110807` (20,156 frames) | Ungraded | Ungraded, use `X` |
| **2nd Half** | **`110808 .. 190197`** (79,390 frames) | **Graded** | **Important**: Kickoff is at frame 113,742; frames 110,808..113,741 are all graded **`D`**! |
| Post-match | `190198 .. 199318` | Ungraded | Ungraded, use `X` |

Total graded frames: **158,857**.

---

### 3. Evaluation & Scoring Rules
- **Primary Ranking Metric: `spellF1`**
  - Evaluates matched possessions (maximal contiguous runs of `H` or `A`, ignoring stoppages `D`).
  - Matches predicted spells to ground truth spells using **temporal IoU** at thresholds `[0.3, 0.4, 0.5, 0.6, 0.7]`, taking the mean F1 across thresholds.
  - Constant guess gets `spellF1 = 0.0000`.
- **Tie-breaker Metric: `macroF1`**
  - Unweighted mean of F1 scores across classes `H`, `A`, and `D` on all graded frames.
- **Baseline Floor**:
  - `baseline_smooth50` achieves full-match `spellF1 = 0.2433` (macroF1: `0.6724`).
- **THE 5-MINUTE TRAP (CRITICAL)**:
  - The public GT (`evaluation/gt/BAR-ATH_possession_gt_public.csv`) covers **only 5 minutes** (frames 11,185..18,684, 17 possessions).
  - **NEVER train or hyperparameter-tune models on the public 5 minutes.** On the public window, `smooth125` looks best (`0.4242`), but on the full match `smooth50` wins (`0.2433` vs `0.2242`).
  - Use the public window solely as an end-to-end integration and sanity check.
- **Abstention (`X`) Behavior**:
  - In `macroF1`: `X` on a graded frame counts as an outright error.
  - In `spellF1`: `X` is **forward-filled** with the half's previous non-`X` prediction.
  - *Strategy*: Abstaining (`X`) during occlusions within an ongoing possession is free and prevents false splits. Abstaining across team transitions is costly because it bleeds the old team label forward.

---

### 4. Input Assets & Data Specs
- **Data Directory**: Default `./data` or path in `$env:MTAH_DATA_DIR`.
- **Tactical Video Feed** (`tactical`):
  - Primary reference for video frames: submission row `i` == video frame `i`.
  - ATD Tracking: 199,319 records. `video_frame = frame_id - 1`.
  - **Ball Missing**: Ball is `NaN` on **41% of graded frames** (occlusions, high balls, box scrambles).
  - 46 Track Slots: Tracklets, NOT fixed player shirt numbers. Slots swap and disconnect.
  - Homography: 199,319 rows. Maps normalized (0..1) pitch coords to pixel space. 100% valid in tactical.
  - Smart Tagging: 638 XML instances (`start` and `end` in seconds from frame 0: `frame = round(sec * 25)`). Notice: 36 tags have `Team: N/A` (all throw-ins).
- **Broadcast Video Feed** (`broadcast`):
  - Unsynchronized timeline (cuts, replays, zoom). 164,488 frames.
  - Homography only 65.8% valid. Do not use without building proper temporal mapping.

---

### 5. Architectural Principle: Football State Machine (spellF1-Driven)
- **Possession is an Inertia State, Not Frame-by-Frame Voting**:
  - Individual frames are noisy observations (41% ball missing, player track switches, brief deflections).
  - When a team has possession, they retain it across passes in flight, loose-ball scrambles, and temporary occlusions.
- **State Machine Structure**:
  - Primary states: `STATE_H`, `STATE_A`, `STATE_D`.
  - **Turnover Guard ($H \leftrightarrow A$)**: Never switch on a single touch. Require opponent controlled possession (sustained proximity, controlled movement) and lookahead verification (ensure ball does not return to original team within ~1s).
  - **Stoppage ($H/A \to D$)**: Triggered by dead ball events (pitch bounds, Smart Tagging set pieces, collective deceleration).
  - **Restart ($D \to H/A$)**: Triggered by set-piece execution / first controlled touch.
- **Why this optimizes spellF1**:
  - `spellF1` ranks whole possession intervals via temporal IoU.
  - False transitions split genuine spells and severely penalize `spellF1`. State continuity and turnover verification preserve whole possession objects.

---

### 6. Competition Constraints & Rules
- **No Manual Annotation**: All predictions on the provided match must be purely algorithmic. No human hand-correction of frames or transitions.
- **No Ground Truth Leakage**: No external Opta/StatsBomb/human event data for this specific match.
- **Public Reproducibility**: The repository must be able to reproduce the submitted CSV deterministically.

---

### 7. Workspace Environment & Execution
- **Python Executable**: Use the local virtual environment: `.\.venv\Scripts\python.exe`.
- **Verification Commands**:
  - Validate submission structure:
    `.\.venv\Scripts\python.exe evaluation/validate_submission.py <path_to_submission.csv>`
  - Run evaluation:
    `.\.venv\Scripts\python.exe evaluation/run_evaluation.py`
  - Compact agent evaluation:
    `.\.venv\Scripts\python.exe tools/agent_eval.py --submission <path_to_submission.csv>`
  - Check dataset presence:
    `.\.venv\Scripts\python.exe tools/data_status.py`
