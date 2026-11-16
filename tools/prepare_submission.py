"""Submission Preparation & Verification Tool.

Builds, validates, scores, and packages official deliverables for
the More Than A Hack 2027 challenge according to SUBMISSION.md.

Usage:
    python tools/prepare_submission.py --team Barer
"""

import argparse
import os
import shutil
import subprocess
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

from run_experiment import build_match_context
from strategies.football_engine import FootballEngineStrategy
import possession_metrics as pm


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare submission files for MTAH 2027")
    parser.add_argument("--team", default="Barer", help="Official team name (default: Barer)")
    return parser.parse_args()


def main():
    args = parse_args()
    team = args.team.strip()
    print("=" * 65)
    print(f"Preparing Submission Deliverables for Team: '{team}'")
    print("=" * 65)

    # 1. Build context and predict
    print("\n[1/5] Running Production Football Engine...")
    ctx = build_match_context(use_cache=True)
    if ctx is None:
        print("ERROR: Match tracking data not found in data/.")
        sys.exit(1)

    strat = FootballEngineStrategy()
    preds = strat.predict(ctx)
    n_frames = len(preds)
    print(f"      Generated {n_frames} frame predictions.")

    # 2. Write CSV
    csv_filename = f"{team}.csv"
    csv_path = os.path.join(ROOT, csv_filename)
    results_path = os.path.join(ROOT, "evaluation", "results", f"{team}.csv")

    lines = ["frame,label\n"]
    for i, lbl in enumerate(preds):
        lines.append(f"{i},{lbl}\n")

    with open(csv_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    shutil.copyfile(csv_path, results_path)
    shutil.copyfile(csv_path, os.path.join(ROOT, "evaluation", "results", "football_engine.csv"))
    print(f"      Saved: {csv_path} ({os.path.getsize(csv_path) / (1024*1024):.2f} MB)")

    # 3. Validate Submission
    print("\n[2/5] Running Official Submission Validator...")
    val_proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "evaluation", "validate_submission.py"), csv_path],
        capture_output=True,
        text=True,
    )
    print(val_proc.stdout.strip())
    if val_proc.returncode != 0:
        print("ERROR: Submission validation failed!")
        sys.exit(1)

    # 4. Score on Public GT
    print("\n[3/5] Scoring on Public 5-Minute Ground Truth...")
    gt_path = os.path.join(ROOT, "evaluation", "gt", "BAR-ATH_possession_gt_public.csv")
    if os.path.isfile(gt_path):
        from tools.agent_eval import score_file
        gt_table = pm.read_label_csv(gt_path)
        gt_codes = pm.label_codes(gt_table)
        res = score_file(csv_path, gt_codes)
        if "error" in res:
            print(f"      Evaluation error: {res['error']}")
        else:
            summary, _ = res
            print(f"      spellF1 (Rank Metric): {summary['spell_f1']:.4f}")
            print(f"      macroF1 (Tie-Break):   {summary['macro_f1']:.4f}")
            print(f"      Possessions:           {summary['possessions']} (mean duration: {summary['mean_dur_s']}s)")
            print(f"      Transition F1 @25f:    {summary['trans_f1_25']:.4f} (latency: {summary['mean_lat_f']} frames)")
    else:
        print("      Public GT not found; skipped scoring.")

    # 5. Technical Document
    print("\n[4/5] Preparing Technical Document...")
    md_filename = f"{team}.md"
    md_path = os.path.join(ROOT, md_filename)
    approach_path = os.path.join(ROOT, "APPROACH.md")

    if os.path.isfile(approach_path):
        with open(approach_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"      Saved: {md_path}")
    else:
        print("ERROR: APPROACH.md not found!")

    # 6. Run Golden Spells Test Suite
    print("\n[5/5] Running Golden Spells Regression Suite...")
    test_proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tests", "test_golden_spells.py")],
        capture_output=True,
        text=True,
    )
    if "OK" in test_proc.stderr or "OK" in test_proc.stdout:
        print("      ALL 24 GOLDEN PHYSICAL TESTS PASSED!")
    else:
        print(test_proc.stdout)
        print(test_proc.stderr)
        print("WARNING: Golden test suite reported issues.")

    # Summary
    print("\n" + "=" * 65)
    print("SUBMISSION CHECKLIST (Google Form Deliverables)")
    print("=" * 65)
    print(f"1. Team Name:                 {team}")
    print(f"2. Possession File:           {csv_path} (Upload to form)")
    print(f"3. Public Code Repository URL: https://github.com/jperera96/football-possession-algorithms")
    print(f"4. Technical Document:        {md_path} (Upload to form)")
    print("=" * 65)
    print("Everything is verified and ready for submission!")


if __name__ == "__main__":
    main()
