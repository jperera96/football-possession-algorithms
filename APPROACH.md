# Team Barer — Technical Document
## Ball Possession Inference via Physical State Machine & Spatio-Temporal Inertia

**Challenge**: More Than A Hack 2027 — Phase 1: Ball Possession  
**Organizers**: Metrica Sports, FC Barcelona, Mobile World Capital Barcelona  
**Match**: FC Barcelona vs Athletic Club (`BAR-ATH`), LaLiga 2024-25 Matchday 2  
**Team Name**: Barer  
**Primary Deliverable**: `evaluation/results/football_engine.csv` (199,319 frames)  
**Public Benchmark**: **`spellF1 = 0.9375`** (Rank Metric) | **`macroF1 = 0.9732`** (First Tie-Breaker)  

---

## 1. The Approach: What We Built and Why

In professional football analytics, **possession is an ongoing state of control with inertia**, not an independent frame-by-frame vote. 

When observing video tracking data, raw measurements are noisy: the ball is untracked or occluded on **41% of graded frames**, player tracklet slots swap during tackles, and high passes spend dozens of frames in flight without any player in physical contact with the ball. 

Conventional approaches typically frame this task as a frame-by-frame classifier (e.g. Random Forests, Gradient Boosted Trees, or MLPs) or apply sliding-window majority voting over player proximities. These methods fail catastrophically on the primary competition metric, **`spellF1`**:
- **Why Frame-by-Frame Fails**: Treating consecutive frames as independent predictions causes severe temporal flickering. A single deflection, bounce, or 1-second tracking occlusion splits a 25-second continuous possession into multiple fragments. In baseline window models, the public 5-minute window fractured 17 genuine possessions into 131 disjoint fragments, yielding a full-match `spellF1` of only `0.2433`.
- **Why Deep Learning Struggles**: Black-box temporal models (such as LSTMs or Transformers) trained on small tracking samples easily overfit to specific player movements, camera angles, or the 5-minute public ground truth, failing to generalize across a full 90-minute match.

### Our Solution: The Physics-Grounded State Machine (`football_engine`)
We built an **inertia-driven continuous state machine** grounded in fundamental football mechanics and the IFAB Laws of the Game. Rather than asking *"who is closest to the ball on frame $t$?"*, our engine models possession as a continuous dynamical state (`STATE_H`, `STATE_A`, `STATE_D`):
1. **Possession Inertia**: Once a team establishes controlled possession, they retain that possession through passes in flight, loose-ball scrambles, aerial duels, and visual occlusions.
2. **Turnover Barrier**: A change of possession ($H \leftrightarrow A$) requires the defending team to physically establish control (sustained proximity, controlled deceleration, or a verified multi-player counter-pass). Momentary deflections or challenged duels never split an ongoing attack.
3. **Physical Stoppage Transitions**: Stoppages ($H/A \to D$) are tied to physical ball boundaries (touchlines and goal lines), set-piece executions, or collective deceleration envelopes, while restarts ($D \to H/A$) synchronize to the kicker striking the ball into play.

---

## 2. Which Assets We Used & How (and What We Dropped)

### Assets Used
1. **Tactical Automatic Tracking (ATD)**:
   - *Primary Spatial Timeline*: Provides pitch coordinates for 46 player slots and the ball across all 199,319 frames.
   - *Goalkeeper Optical Slot Disambiguation*: Because goalkeepers wear distinct kit colors, the optical tracker frequently swapped which goalkeeper occupied slot `23` vs slot `45` across 18,000 frames (12 minutes). We implemented deterministic slot identity disambiguation based on team defending halves.
   - *Dynamic Optical Tracklet Swap Resolution*: In crowded box situations where an attacker crossed with a defender and was tracked under a temporary slot, we track kinematic continuity across the dropout gap to preserve continuous attack spells.
2. **Smart Tagging XML**:
   - Used as a prior for set pieces (kickoffs, throw-ins, corner kicks, free kicks, goals).
   - *Set-Piece Prior Refinement*: We clamped overlapping lookback windows to prevent dead-ball tags from erasing preceding live possessions, and recovered pre-goal attacking build-ups by identifying the exact post-shot celebration freeze.
3. **Pitch Homography (Tactical)**:
   - 100% valid across all 199,319 frames; used to project normalized tracking coordinates to standardized metric pitch dimensions ($105\text{ m} \times 68\text{ m}$).

### Assets Dropped
- **Broadcast Video & Broadcast Homography**:
  - We explicitly dropped the broadcast feed from our pipeline.
  - *Why*: The broadcast video contains television production cuts, slow-motion replays, and close-up camera angles that break temporal synchrony with match time. Furthermore, broadcast homography is missing or invalid on **34.2% of frames**. Integrating the broadcast feed would introduce temporal phase lag, camera cut artifacts, and spatial noise into an otherwise clean physical coordinate space.

---

## 3. Training Data & Compliance

- **No External Data**: We used zero external data sources. No StatsBomb, Opta, Wyscout, or external match data of any kind was used.
- **Zero Ground-Truth Training / Tuning**: Not a single frame from the provided match was used for model training or machine learning parameter optimization.
- **Avoiding the "5-Minute Trap"**: The public ground truth covers only 5 minutes (frames 11,185..18,684, containing 17 possessions). Optimizing hyper-parameters on this 5-minute slice leads to severe overfitting (for example, rolling window size 125 appears optimal on the 5-minute GT but scores poorly on the full 90-minute match). We treated the public ground truth strictly as an end-to-end integration and sanity check.
- **Algorithmic Determinism**: The engine is 100% deterministic, rule-verified, and derived from physical kinematics and IFAB football laws.

---

## 4. Possession Rules Implemented

Our engine implements clear physical rules for edge cases:

1. **Turnover Barrier ($H \leftrightarrow A$)**:
   - A team in possession retains the ball across passes in flight ($v_{ball} > 8\text{ m/s}$) even if the ball flies near an opposing player. An opponent must accumulate sustained evidence ($E_{opp} > E_{poss} + 11$) before a turnover is recognized.
2. **Contested Duels & Deflections**:
   - A defending player challenging or deflecting the ball during an ongoing attacking sequence does not constitute a turnover unless the defending team establishes controlled team possession. Brief contested interactions without a pass or forward progression are merged into the surrounding attack.
3. **Defensive Clearances**:
   - A clearance must be an active physical strike ($v_{ball} \ge 6\text{ m/s}$ with acceleration surge) that reverses ball motion away from the defending goal. A fast pass flying past a defending marker is never misclassified as a clearance.
4. **Goalkeeper Hand-Held Possession (IFAB Law 12)**:
   - When a goalkeeper catches or collects the ball inside their own penalty box, the ball is legally alive under IFAB Law 12. Possession is preserved across hand-held occlusions (`NaN` tracking) and run-up preparation for up to 26 seconds until the service punt or throw.
5. **Stationary Ball Restarts (IFAB Law 13)**:
   - Under IFAB Law 13, all free kicks must be taken from a stationary ball ($\Delta d_{ball} \le 0.65\text{ m}$). This physical constraint eliminates false dead-ball triggers during live build-up passing sequences while ensuring genuine foul and offside restarts snap cleanly to the kicker's strike.

---

## 5. Limitations & Future Work

While the engine achieves `spellF1 = 0.9375` and zero spurious possession splits on the public benchmark, certain real-world edge cases remain challenging:
1. **2D Projection of Aerial Trajectories**:
   - When a goalkeeper launches a high goal kick or punt, 2D pitch homography projects the ball centroid onto the grass, making high-altitude trajectories appear as distorted non-linear paths. With more time, we would implement a 3D ballistic parabola filter to model the true apex and flight time.
2. **In-Pitch Whistle Detection During Stoppages**:
   - When a referee whistles for a foul in open play without an out-of-bounds trigger, players sometimes mill around or hold the ball without kicking it out. Step 11 detects collective deceleration, but having synchronized referee whistle audio would allow millisecond-level stoppage snapping.
3. **Prolonged Goalmouth Scrambles**:
   - When 8 to 10 players pack the six-yard box and the ball is occluded for $> 30\text{ seconds}$, determining possession before the ball re-emerges relies on post-reappearance evidence. Optical player pose estimation could help disambiguate body orientation in congested scuffles.

---

## 6. Reproduction & Execution Instructions

The repository is self-contained and reproducible on any system running Python 3.8+:

### 1. Environment Setup
```bash
# Clone repository and enter directory
git clone https://github.com/jperera96/football-possession-algorithms.git
cd football-possession-algorithms

# Install core dependencies (numpy and pandas only)
pip install -r requirements.txt
```

### 2. Generate the Submission File
```bash
# Runs the production engine and produces the submission CSV in ~6 seconds
python run_experiment.py --strategy football_engine
```
The output file is written to:
`evaluation/results/football_engine.csv` (199,319 rows, `frame,label`).

### 3. Verify Submission Format Contract
```bash
python evaluation/validate_submission.py evaluation/results/football_engine.csv
```

### 4. Run the Full Test & Regression Guard
```bash
# Run the 24 golden physical regression test cases
python tests/test_golden_spells.py

# Verify zero unintended changes across the full 90-minute match
python tools/regression_check.py
```
