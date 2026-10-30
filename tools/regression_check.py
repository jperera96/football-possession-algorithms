"""Regression guard for the football_engine strategy.

Three checks, all deterministic:
  1. METRIC FLOOR  - public-window spellF1 / macroF1 must not drop below the floors.
  2. FULL-MATCH DIFF - the full-match output is run-length encoded and diffed against a committed
     baseline (tests/baseline/football_engine_segments.json). Every changed region is listed with
     its length so an intended fix can be told apart from collateral damage. Public GT covers only
     5 minutes, so this is the only way to see regressions over the other ~85 minutes.
  3. SNAPSHOT HASH - sha256 of the label stream, shown with the diff.

Usage:
    python tools/regression_check.py                 # check; exit 1 on floor breach or unexpected diff
    python tools/regression_check.py --update        # accept current output as the new baseline
    python tools/regression_check.py --max-diff-frames 2000   # allow up to N changed frames
    python tools/regression_check.py --submission path.csv    # check an existing CSV instead

Workflow for a change: run it, read the diff, confirm every flipped region is intended, then
run with --update and commit the baseline together with the code change.
"""

import argparse
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

import possession_metrics as pm  # noqa: E402
from games import GAME  # noqa: E402

BASELINE = os.path.join(ROOT, "tests", "baseline", "football_engine_segments.json")
FLOOR = {"spell_f1": 0.9375, "macro_f1": 0.9730}


def rle(labels):
    segs, i, n = [], 0, len(labels)
    while i < n:
        j = i
        while j < n and labels[j] == labels[i]:
            j += 1
        segs.append([i, j, str(labels[i])])
        i = j
    return segs


def expand(segs, n):
    out = np.full(n, "X", dtype="<U1")
    for a, b, v in segs:
        out[a:b] = v
    return out


def get_predictions(csv_path):
    if csv_path:
        return pm.read_label_csv(csv_path)["label"].to_numpy().astype("<U1")
    from run_experiment import build_match_context
    from strategies.football_engine import FootballEngineStrategy

    return FootballEngineStrategy().predict(build_match_context(use_cache=True))


def public_metrics(preds):
    gt_path = os.path.join(ROOT, "evaluation", "gt", f"{GAME}_possession_gt_public.csv")
    gt_codes = pm.label_codes(pm.read_label_csv(gt_path))
    pred_codes = pm.label_codes(preds)
    m = pm.evaluate(gt_codes, pred_codes)
    return float(m["spell_f1_mean"]), float(m["macro_f1"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update", action="store_true", help="accept current output as new baseline")
    ap.add_argument("--submission", default=None, help="check an existing CSV instead of re-running the engine")
    ap.add_argument("--max-diff-frames", type=int, default=0, help="tolerated number of changed frames")
    ap.add_argument("--show", type=int, default=40, help="max changed regions to print")
    args = ap.parse_args()

    preds = get_predictions(args.submission)
    n = len(preds)
    digest = hashlib.sha256("".join(preds).encode()).hexdigest()[:16]
    failed = False

    spell, macro = public_metrics(preds)
    print(f"public spellF1={spell:.4f} (floor {FLOOR['spell_f1']})  macroF1={macro:.4f} (floor {FLOOR['macro_f1']})")
    if spell < FLOOR["spell_f1"] - 1e-9 or macro < FLOOR["macro_f1"] - 1e-9:
        print("FAIL: public metric below floor")
        failed = True

    if args.update:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        with open(BASELINE, "w") as f:
            json.dump({"n": n, "sha256_16": digest, "segments": rle(preds)}, f)
        print(f"baseline updated: {BASELINE} (hash {digest})")
        sys.exit(1 if failed else 0)

    if not os.path.isfile(BASELINE):
        print(f"No baseline at {BASELINE}; run with --update first.")
        sys.exit(1)
    with open(BASELINE) as f:
        base = json.load(f)
    old = expand(base["segments"], base["n"])
    if base["n"] != n:
        print(f"FAIL: row count {n} != baseline {base['n']}")
        sys.exit(1)

    diff = old != preds
    n_diff = int(diff.sum())
    print(f"snapshot hash {digest} (baseline {base['sha256_16']}) | changed frames: {n_diff} ({n_diff / 25:.1f}s)")
    if n_diff:
        i, shown = 0, 0
        while i < n:
            if diff[i]:
                j = i
                while j < n and diff[j]:
                    j += 1
                if shown < args.show:
                    o = "".join(sorted(set(old[i:j])))
                    p = "".join(sorted(set(preds[i:j])))
                    print(f"  [{i:6d}..{j:6d}) {j - i:5d}f {(j - i) / 25:6.2f}s  {o} -> {p}")
                shown += 1
                i = j
            else:
                i += 1
        print(f"  {shown} changed region(s)")
        if n_diff > args.max_diff_frames:
            print("FAIL: unexpected full-match change. If intended: verify regions above, then --update.")
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
