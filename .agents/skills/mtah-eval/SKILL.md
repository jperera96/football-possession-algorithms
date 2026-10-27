---
name: mtah-eval
description: >-
  Use this skill when evaluating, validating, or diagnosing possession model predictions
  for the More Than A Hack 2027 hackathon. Covers submission validation, interpreting
  spellF1 vs macroF1, transition metrics, latency, and avoiding the 5-minute trap.
---

# More Than A Hack 2027: Evaluation & Diagnostics

## 1. Validating a Submission File
Before evaluating or submitting any file, validate its structure:
```powershell
.\.venv\Scripts\python.exe evaluation/validate_submission.py <path_to_submission.csv>
```

### Strict Requirements Checked:
1. Header is exactly `frame,label`.
2. Exactly 199,319 data rows (frames 0 to 199318 in sequential order).
3. Labels are strictly `H`, `A`, `D`, or `X`.
4. No empty or missing cells.

A malformed file is skipped automatically by the official scorer and receives zero points.

---

## 2. Running Evaluation
To score all files in `evaluation/results/` against the public 5-minute ground truth:
```powershell
.\.venv\Scripts\python.exe evaluation/run_evaluation.py
```

To evaluate a specific submission file using the compact agent evaluation tool:
```powershell
.\.venv\Scripts\python.exe tools/agent_eval.py --submission evaluation/results/<file>.csv
```

To compute segment-bootstrap confidence intervals:
```powershell
.\.venv\Scripts\python.exe evaluation/run_evaluation.py --bootstrap 1000
```

---

## 3. Scoreboard Metric Guide
The evaluation output contains several critical columns:

| Column | Metric | Description | Target / Benchmark |
|---|---|---|---|
| `spellF1` | Mean Spell F1 | **Primary ranking metric**. Temporal IoU F1 of matched possessions over IoU thresholds `[0.3, 0.4, 0.5, 0.6, 0.7]`. Requires continuous, realistic possession runs. | > 0.2433 (Baseline smooth50 is 0.2433 on full match) |
| `macroF1` | Macro-averaged F1 | **Tie-breaker**. Frame-level unweighted average of F1 for `H`, `A`, and `D` on graded frames. | Baseline ~0.67 |
| `poss` | Predicted Possessions | Number of predicted possession segments. Compare against ground truth segments. High `poss` indicates flickering / under-smoothing. | Truth ~17 per 5 min |
| `dur` | Mean Duration (s) | Mean possession length in seconds. | Truth ~14.2s on public GT |
| `transF1` | Transition F1 | Precision/recall of detecting transition boundaries within $\pm 25$ frames ($\pm 1.0$ s). | Higher is better |
| `lat_f` | Mean Latency (frames) | Frame lag of detected transitions. Positive = late prediction, Negative = early prediction. | Near 0.0 |
| `shareE` | Possession Share Error | Absolute error between predicted and true Home possession share. | Near 0.0 |
| `frag` | Fragmentation Ratio | Ratio of predicted segments to GT segments. Values > 1.5 indicate severe oversegmentation. | Near 1.0 |

---

## 4. The 5-Minute Overfitting Trap
- The public GT contains only **17 possessions** across 5 minutes.
- A single boundary difference or missed segment moves `spellF1` by $\approx 0.06$.
- `baseline_smooth125` scored **0.4242** on public GT, but dropped to **0.2242** on full match.
- `baseline_smooth50` scored **0.3256** on public GT, but won on full match with **0.2433**.
- **Rule of Thumb**:
  - Check public GT only for pipeline sanity, frame alignment, and basic sanity checks.
  - Rely on principled modeling (domain rules, physics constraints, HMM transition priors, Smart Tagging) rather than hyperparameter tuning against the public 5 minutes.
