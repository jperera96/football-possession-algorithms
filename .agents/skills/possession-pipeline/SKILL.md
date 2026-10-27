---
name: possession-pipeline
description: >-
  Use this skill when developing, designing, or improving algorithms for football ball
  possession inference from tracking and video metadata. Covers the Football State Machine
  architecture, possession inertia, turnover verification with lookahead, dead-ball detection,
  and optimizing directly for spellF1 rather than per-frame macroF1.
---

# Football Possession Pipeline: State Machine Architecture

## 1. Core Philosophy: Possession is an Inertia-Driven State

In football, **individual frames are noisy observations, not ground truth**. 
- The ball is missing on **41% of graded frames**.
- Passes in the air, deflections, contested duels, and momentary touches happen continuously.
- **Possession is an enduring state with high inertia**:
  - A ball in flight from Player $H_1$ to $H_2$ belongs to $H$ for the entire pass.
  - A defender deflecting a pass does *not* win possession unless that defender or a teammate gains controlled possession.
  - In 50/50 loose balls and scrambles, possession remains with the team that had it last until the opponent establishes control.
- **Optimizing for `spellF1` over `macroF1`**:
  - `macroF1` rewards micro-accuracy at individual frames, often encouraging flickering classifications that fragment possessions.
  - `spellF1` evaluates **whole possession objects** matched by temporal IoU (`[0.3..0.7]`). A single false transition splits a true 20-second possession into two fragments, instantly destroying the IoU match and creating spurious spells.
  - Therefore, the system must prioritize **state continuity** and **deliberate, high-confidence transitions**.

---

## 2. The Football Finite State Machine (FSM)

```
                 ┌──────────────────────────────────────────────┐
                 │                                              │
                 ▼                                              │
        ┌─────────────────┐       Turnover (High Confidence)   ┌─────────────────┐
        │  Possession: H  │ ─────────────────────────────────> │  Possession: A  │
        │   (Barcelona)   │ <───────────────────────────────── │ (Athletic Club) │
        └─────────────────┘       Turnover (High Confidence)   └─────────────────┘
                 │     ▲                                                ▲     │
        Stoppage │     │ Restart (H)                        Restart (A) │     │ Stoppage
                 ▼     │                                                │     ▼
        ┌────────────────────────────────────────────────────────────────────────┐
        │                           Dead Ball State (D)                          │
        │                       (Out of play / Stoppage)                         │
        └────────────────────────────────────────────────────────────────────────┘
```

### Primary States:
1. **`STATE_H`**: Home team (Barcelona) in controlled possession.
2. **`STATE_A`**: Away team (Athletic Club) in controlled possession.
3. **`STATE_D`**: Dead ball / stoppage.
4. *(Ungraded intervals: `< 11185`, halftime `90652..110807`, and `> 190197` default to `X`)*.

---

## 3. State Transition Rules & Evidence Gathering

### A. Possession Inertia (Default Rule)
```python
if current_state in (STATE_H, STATE_A):
    # By default, MAINTAIN previous possession
    next_state = current_state
```
Do **not** change possession because of:
- Missing ball frames (`NaN` in ATD).
- Single-frame proximity spikes from an opponent.
- Brief loose-ball phases during passes or clearances.

---

### B. Turnover Transitions ($H \to A$ or $A \to H$)
A change of possession occurs **only when the opposing team establishes controlled possession**.

#### Turnover Guard Conditions (All must be satisfied):
1. **Sustained Proximity**: Opponent player is within control radius ($r \le 2.0$–$2.5$ m) for at least $k_{min}$ consecutive frames (e.g. 10–15 frames / 0.4–0.6 s).
2. **Controlled Movement / Pass**: Opponent moves with the ball or connects with an opponent teammate.
3. **Lookahead / Hysteresis Verification**:
   - Because we process the full match offline, inspect a forward window ($t + 1 .. t + W$, e.g. 15–25 frames / 0.6–1.0 s).
   - If the ball returns to the original possessor within the window, the event was a **rebound or deflection**, NOT a turnover. The state remains unchanged.

---

### C. Stoppage Transitions ($H/A \to D$)
A possession spell ends when play halts:
1. **Pre-kickoff Dead Periods**:
   - 2nd half frames `110808 .. 113741` are all **`D`** (before the 2nd half kickoff at `113742`).
2. **Out of Bounds**:
   - Ball coordinates outside normalized pitch $[0, 1] \times [0, 1]$ (with tolerance).
3. **Smart Tagging Set Piece Windows**:
   - Metrica Smart Tagging marks set pieces (`Throw-in`, `Corner Kick`, `Goal Kick`, `Free Kick`, `Kick Off`).
   - The period immediately preceding the tagged restart execution is dead ball (`D`).
4. **Kinematic Deceleration**:
   - Tracking shows ball stoppage or all players decelerating below walking speed ($< 1.2$ m/s).

---

### D. Restart Transitions ($D \to H/A$)
Play restarts from a dead-ball state:
1. **Smart Tagging Tag Evidence**:
   - Set pieces often tag the executing team: `Team: Barcelona` $\to H$, `Team: Atletic Club` $\to A$.
   - *Caution*: 36 tags (especially throw-ins) have `Team: N/A`. For these, identify the first player initiating ball motion at the restart point.
2. **Kickoff Events**:
   - 1st Half kickoff (`11185`): away team or home team restart.
   - 2nd Half kickoff (`113742`): opposite team restart.
3. **First Controlled Touch**:
   - The first player to strike the stationary ball initiates the new possession state.

---

## 4. Frame Evidence as Observation Likelihoods

Treat per-frame metrics not as hard votes, but as emission probabilities / observation evidence fed into the state machine:

| Feature / Signal | Description | State Impact |
|---|---|---|
| `ball_dist_H`, `ball_dist_A` | Min distance to Home/Away player | Evidence of control |
| `ball_visible` | Ball tracking is non-NaN | Confidence weight |
| `player_ball_vel_align` | Dot product of player & ball velocity | Directional control evidence |
| `smart_tag_phase` | Active phase (`BUILD UP`, `SET PIECES`, etc.) | Team prior & state constraints |
| `pitch_boundary_violation` | Ball outside pitch boundaries | High likelihood of `STATE_D` |

---

## 5. Summary Checklist for SpellF1 Optimization

- [x] **State Machine over Frame Classifier**: Transition logic determines changes; inertia maintains states.
- [x] **No Single-Touch Turnovers**: Require sustained control and check forward lookahead to ignore deflections.
- [x] **Bridge Missing Ball**: Ball missing is not a transition; keep current state.
- [x] **Precise Dead-Ball Demarcation**: Split possessions only at real stoppages (`D`) or established turnovers.
- [x] **Realistic Possession Count**: Ground truth has ~17 possessions per 5 minutes (mean duration ~14s). If a model predicts 100+ possessions, the turnover threshold is too sensitive.
