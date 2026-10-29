"""Unified Experiment Runner & Strategy Benchmark Harness.

Executes, tests, scores, and documents independent possession strategies.

Usage:
    python run_experiment.py --list
    python run_experiment.py --test-all
    python run_experiment.py --strategy fsm_lookahead --notes "Baseline FSM with 25-frame lookahead"
    python run_experiment.py --strategy all
"""

import argparse
import json
import os
import sys
import time
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "evaluation"))

from games import GAME, GAMES, asset_paths, half_video_blocks  # noqa: E402
import possession_metrics as pm  # noqa: E402
from strategies import STRATEGY_REGISTRY, get_strategy, list_strategies  # noqa: E402
from strategies.base import TrackingContext  # noqa: E402
from pipeline.dead_ball import (
    init_frame_mask,
    parse_smart_tagging_stoppages,
    apply_pitch_boundary_dead_balls,
    bridge_out_of_bounds_to_set_pieces,
    resolve_throw_in_restart_teams,
)  # noqa: E402
from pipeline.runner import load_player_teams_from_meta  # noqa: E402
from tools.agent_eval import score_file  # noqa: E402


def build_match_context(use_cache=True):
    """Build TrackingContext from downloaded assets (with optional fast npz cache)."""
    paths = asset_paths(source="tactical")
    n_frames = GAMES[GAME]["n_video_frames"]

    if not os.path.isfile(paths["atd_raw"]) or not os.path.isfile(paths["atd_meta"]):
        return None

    cache_file = os.path.join(HERE, "data", "cache", "tracking_context.npz")
    if use_cache and os.path.isfile(cache_file):
        cached = np.load(cache_file)
        ball_coords = cached["ball_coords"]
        player_coords = cached["player_coords"]
        player_teams = cached["player_teams"]
        dead_mask = cached["dead_ball_mask"]

        restarts = {11185: "A", 113742: "H"}
        stoppages = []
        if os.path.isfile(paths["smart_tagging"]):
            stoppages = parse_smart_tagging_stoppages(paths["smart_tagging"])
            for s in stoppages:
                if s.get("restart_team") in ("H", "A"):
                    restarts[s["restart_frame"]] = s["restart_team"]
                elif s["team"].lower() in ("barcelona", "h"):
                    restarts[s["restart_frame"]] = "H"
                elif s["team"].lower() in ("atletic club", "athletic club", "a"):
                    restarts[s["restart_frame"]] = "A"

            throw_in_restarts = resolve_throw_in_restart_teams(stoppages, player_coords, player_teams, n_frames)
            restarts.update(throw_in_restarts)

        return TrackingContext(
            n_frames=n_frames,
            ball_coords=ball_coords,
            player_coords=player_coords,
            player_teams=player_teams,
            dead_ball_mask=dead_mask,
            restarts=restarts,
            smart_tagging_stoppages=stoppages,
        )

    # 1. Base boundaries
    dead_mask = init_frame_mask(n_frames)

    # 2. Smart Tagging
    restarts = {11185: "A", 113742: "H"}
    stoppages = []
    if os.path.isfile(paths["smart_tagging"]):
        stoppages = parse_smart_tagging_stoppages(paths["smart_tagging"])
        for s in stoppages:
            d_start = max(0, s["dead_start"])
            d_end = min(n_frames - 1, s["dead_end"])
            for f in range(d_start, d_end):
                if dead_mask[f] == "":
                    dead_mask[f] = "D"
            if s.get("restart_team") in ("H", "A"):
                restarts[s["restart_frame"]] = s["restart_team"]
            elif s["team"].lower() in ("barcelona", "h"):
                restarts[s["restart_frame"]] = "H"
            elif s["team"].lower() in ("atletic club", "athletic club", "a"):
                restarts[s["restart_frame"]] = "A"

    # 3. Stream tracking
    player_teams = load_player_teams_from_meta(paths["atd_meta"])
    n_slots = len(player_teams)
    ball_coords = np.full((n_frames, 2), np.nan, dtype=np.float32)
    player_coords = np.full((n_frames, n_slots, 2), np.nan, dtype=np.float32)

    with open(paths["atd_raw"], "r") as handle:
        for line in handle:
            parts = line.strip().split(":")
            if len(parts) != 3:
                continue
            v_frame = int(parts[0]) - 1
            if not (0 <= v_frame < n_frames):
                continue

            # Players
            p_str = parts[1]
            if p_str:
                for idx, item in enumerate(p_str.split(";")):
                    if idx >= n_slots:
                        break
                    vals = item.split(",")
                    if len(vals) >= 2 and vals[0] != "NaN" and vals[1] != "NaN":
                        player_coords[v_frame, idx, 0] = float(vals[0])
                        player_coords[v_frame, idx, 1] = float(vals[1])

            # Ball
            b_str = parts[2]
            if b_str:
                vals = b_str.split(",")
                if len(vals) >= 2 and vals[0] != "NaN" and vals[1] != "NaN":
                    ball_coords[v_frame, 0] = float(vals[0])
                    ball_coords[v_frame, 1] = float(vals[1])

    apply_pitch_boundary_dead_balls(dead_mask, ball_coords, tolerance=0.005)
    bridge_out_of_bounds_to_set_pieces(dead_mask, stoppages)

    # Resolve throw-in restart teams from sideline positioning
    throw_in_restarts = resolve_throw_in_restart_teams(stoppages, player_coords, player_teams, n_frames)
    restarts.update(throw_in_restarts)

    return TrackingContext(
        n_frames=n_frames,
        ball_coords=ball_coords,
        player_coords=player_coords,
        player_teams=player_teams,
        dead_ball_mask=dead_mask,
        restarts=restarts,
        smart_tagging_stoppages=stoppages,
    )


def log_experiment(summary, params, notes=""):
    """Update experiments/history.jsonl and experiments/EXPERIMENT_LOG.md."""
    exp_dir = os.path.join(HERE, "experiments")
    os.makedirs(exp_dir, exist_ok=True)

    # 1. JSONL log
    log_path = os.path.join(exp_dir, "history.jsonl")
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        **summary,
        "params": params,
        "notes": notes,
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # 2. Markdown log
    md_path = os.path.join(exp_dir, "EXPERIMENT_LOG.md")
    if not os.path.isfile(md_path):
        with open(md_path, "w") as f:
            f.write("# Strategy Experiment Log & Benchmark Board\n\n")
            f.write("| Timestamp | Strategy / File | spellF1 | macroF1 | Poss | Dur(s) | Frag | Notes |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")

    row = (
        f"| {entry['timestamp']} | `{summary['file']}` | **{summary['spell_f1']:.4f}** | "
        f"{summary['macro_f1']:.4f} | {summary['possessions']} | {summary['mean_dur_s']} | "
        f"{summary['frag_ratio']} | {notes} |\n"
    )
    with open(md_path, "a") as f:
        f.write(row)


def execute_strategy(strat_name, ctx, gt_codes, notes=""):
    """Run an individual strategy, write submission, and score it."""
    strat = get_strategy(strat_name)
    print(f"\n---> Running Strategy: {strat_name}")
    print(f"     Description: {strat.description}")

    t0 = time.time()
    preds = strat.predict(ctx)
    elapsed = time.time() - t0

    out_csv = os.path.join(HERE, "evaluation", "results", f"{strat_name}.csv")
    df = pd.DataFrame({"frame": np.arange(len(preds), dtype=np.int64), "label": preds})
    df.to_csv(out_csv, index=False)

    print(f"     Generated {len(preds)} frames in {elapsed:.1f}s -> {os.path.basename(out_csv)}")
    summary, _ = score_file(out_csv, gt_codes)
    log_experiment(summary, strat.get_params(), notes=notes)

    print(f"     [Result] spellF1: {summary['spell_f1']:.4f} | macroF1: {summary['macro_f1']:.4f} | Poss: {summary['possessions']} | Dur: {summary['mean_dur_s']}s")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Unified Possession Strategy Runner & Benchmark Harness")
    parser.add_argument("--list", action="store_true", help="List all registered strategies")
    parser.add_argument("--test-all", action="store_true", help="Run synthetic unit tests on all strategies")
    parser.add_argument("--strategy", "-s", default="fsm_lookahead", help="Strategy to run (or 'all')")
    parser.add_argument("--notes", "-n", default="", help="Experiment description / notes for the log")
    args = parser.parse_args()

    if args.list:
        print("=" * 75)
        print("Available Possession Strategies:")
        print("=" * 75)
        for name, desc in list_strategies().items():
            print(f"  * {name:<22} : {desc}")
        print("=" * 75)
        return

    if args.test_all:
        print("=" * 75)
        print("Testing all strategies on synthetic sequences...")
        print("=" * 75)
        all_ok = True
        for name in STRATEGY_REGISTRY:
            strat = get_strategy(name)
            try:
                ok = strat.test_synthetic()
                status = "PASSED" if ok else "FAILED"
            except Exception as e:
                status = f"ERROR: {e}"
                all_ok = False
            print(f"  {name:<24} : [{status}]")
        print("=" * 75)
        if all_ok:
            print("ALL STRATEGIES PASSED SYNTHETIC UNIT TESTS!")
        return

    # Check match assets
    ctx = build_match_context()
    if ctx is None:
        print("Match tracking assets not found in ./data. Please unpack the data bundle.")
        sys.exit(1)

    gt_path = os.path.join(HERE, "evaluation", "gt", f"{GAME}_possession_gt_public.csv")
    gt_codes = pm.label_codes(pm.read_label_csv(gt_path))

    targets = list(STRATEGY_REGISTRY.keys()) if args.strategy == "all" else [args.strategy]

    print("=" * 80)
    print(f"Executing {len(targets)} Possession Strategy Experiments")
    print("=" * 80)

    for target in targets:
        execute_strategy(target, ctx, gt_codes, notes=args.notes)

    print("\nAll experiments completed and logged to experiments/EXPERIMENT_LOG.md")


if __name__ == "__main__":
    main()
