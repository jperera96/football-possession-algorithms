# Experiment Tracking & Log

This directory records experimental iterations and model submission runs.

## Files
- `history.jsonl`: Machine-readable log of evaluations recorded via `python tools/agent_eval.py --submission <path> --log --notes "<description>"`.
- Model checkpoints, configuration YAMLs/JSONs, and candidate prediction CSVs.

## Benchmarks (Full Match vs Public GT)
| Model / Submission | Public GT spellF1 | Full Match spellF1 (Official) | Notes |
|---|---|---|---|
| `baseline_smooth50.csv` | 0.3256 | **0.2433** | **Official Baseline Floor to Beat** |
| `baseline_smooth125.csv` | **0.4242** | 0.2242 | Overfits public window; overly aggressive smoothing |
| `baseline_smooth25.csv` | 0.2868 | 0.1996 | Under-smoothed |
| `baseline_raw.csv` | 0.0378 | 0.0486 | Unsmoothed, massive flicker |
