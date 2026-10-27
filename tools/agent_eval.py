"""Agent-friendly submission evaluation and diagnostics tool.

Validates the submission format and scores it against the ground truth.
Outputs a clean, token-efficient summary.

Usage:
    python tools/agent_eval.py --submission evaluation/results/baseline_smooth50.csv
    python tools/agent_eval.py --submission <path> --compare
    python tools/agent_eval.py --submission <path> --json
"""

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

import possession_metrics as pm  # noqa: E402
from games import GAME, GAMES, half_video_blocks  # noqa: E402


def score_file(csv_path, gt_codes):
    """Validate and score a single CSV submission."""
    if not os.path.isfile(csv_path):
        return {"error": f"File not found: {csv_path}"}

    try:
        table = pm.read_label_csv(csv_path)
    except Exception as e:
        return {"error": f"CSV parse error: {e}"}

    expected_rows = GAMES[GAME]["n_video_frames"]
    validation_err = pm.validate_submission(table, expected_rows)
    if validation_err:
        return {"error": f"Validation failed: {validation_err}"}

    pred_codes = pm.label_codes(table)
    metrics = pm.evaluate(gt_codes, pred_codes)

    tau_25 = metrics["transitions"][25]
    summary = {
        "file": os.path.basename(csv_path),
        "valid": True,
        "spell_f1": round(float(metrics["spell_f1_mean"]), 4),
        "macro_f1": round(float(metrics["macro_f1"]), 4),
        "f1_H": round(float(metrics["per_class"]["H"]["f1"]), 4),
        "f1_A": round(float(metrics["per_class"]["A"]["f1"]), 4),
        "f1_D": round(float(metrics["per_class"]["D"]["f1"]), 4),
        "possessions": int(metrics["n_pred_spells"]),
        "mean_dur_s": round(float(metrics["mean_spell_duration_s"]), 1),
        "trans_f1_25": round(float(tau_25["f1"]), 4),
        "mean_lat_f": round(float(tau_25["mean_latency"]), 1) if tau_25["mean_latency"] is not None else None,
        "frag_ratio": round(float(metrics["fragmentation"]), 2),
        "share_err": round(float(metrics["share_err"]), 4) if metrics["share_defined"] else None,
        "abstained_frames": int(metrics["n_abstain_on_graded"]),
    }
    return summary, metrics


def main():
    parser = argparse.ArgumentParser(description="AI Agent possession evaluation helper")
    parser.add_argument("--submission", "-s", required=True, help="Path to submission CSV")
    parser.add_argument("--gt", default=os.path.join(ROOT, "evaluation", "gt", f"{GAME}_possession_gt_public.csv"))
    parser.add_argument("--compare", "-c", action="store_true", help="Compare with baseline results")
    parser.add_argument("--json", "-j", action="store_true", help="Output pure JSON")
    parser.add_argument("--log", "-l", action="store_true", help="Log to experiments/history.jsonl")
    parser.add_argument("--notes", default="", help="Optional notes for logging")
    args = parser.parse_args()

    if not os.path.isfile(args.gt):
        print(f"ERROR: Ground truth file not found: {args.gt}")
        sys.exit(1)

    gt_table = pm.read_label_csv(args.gt)
    gt_codes = pm.label_codes(gt_table)
    res = score_file(args.submission, gt_codes)
    if "error" in res:
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"FAILED: {res['error']}")
        sys.exit(1)

    summary, raw_metrics = res

    if args.log:
        exp_dir = os.path.join(ROOT, "experiments")
        os.makedirs(exp_dir, exist_ok=True)
        log_path = os.path.join(exp_dir, "history.jsonl")
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            **summary,
            "notes": args.notes,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        summary["logged_to"] = log_path

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print("=" * 82)
    print(f"Evaluation Summary: {summary['file']}")
    print("=" * 82)
    print(f"  spellF1 (Rank Metric):  {summary['spell_f1']:.4f}")
    print(f"  macroF1 (Tie-Break):   {summary['macro_f1']:.4f}  [H: {summary['f1_H']:.4f} | A: {summary['f1_A']:.4f} | D: {summary['f1_D']:.4f}]")
    print(f"  Possessions / Dur (s): {summary['possessions']} / {summary['mean_dur_s']}s (GT has 17 / 14.2s)")
    print(f"  Transitions F1 @25f:   {summary['trans_f1_25']:.4f} (latency: {summary['mean_lat_f']} frames)")
    print(f"  Fragmentation Ratio:   {summary['frag_ratio']:.2f}")
    print(f"  Abstained Frames (X):  {summary['abstained_frames']}")
    print("-" * 82)

    if args.compare:
        baselines = [
            ("baseline_smooth50.csv", "Floor Baseline"),
            ("baseline_smooth125.csv", "Wide Smooth"),
            ("baseline_smooth25.csv", "Narrow Smooth"),
            ("baseline_raw.csv", "Raw Unsmoothed"),
        ]
        results_dir = os.path.join(ROOT, "evaluation", "results")
        print("\nBenchmark Comparison on Public GT:")
        print(f"{'Submission':<25} {'spellF1':<10} {'macroF1':<10} {'Poss':<6} {'Dur(s)':<8} {'Frag':<6}")
        print("-" * 68)
        # Print evaluated file first
        print(f"{summary['file']:<25} {summary['spell_f1']:<10.4f} {summary['macro_f1']:<10.4f} {summary['possessions']:<6} {summary['mean_dur_s']:<8.1f} {summary['frag_ratio']:<6.2f} <-- current")
        for b_file, desc in baselines:
            b_path = os.path.join(results_dir, b_file)
            if os.path.isfile(b_path):
                b_res = score_file(b_path, gt_codes)
                if "error" not in b_res:
                    b_sum = b_res[0]
                    print(f"{b_file:<25} {b_sum['spell_f1']:<10.4f} {b_sum['macro_f1']:<10.4f} {b_sum['possessions']:<6} {b_sum['mean_dur_s']:<8.1f} {b_sum['frag_ratio']:<6.2f}")
        print("=" * 82)


if __name__ == "__main__":
    main()
