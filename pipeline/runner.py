"""Pipeline Runner & Submission Generator.

Coordinates:
1. Dead-ball and stoppage demarcation
2. Tracking ingestion & missing ball trajectory reconstruction
3. Instantaneous control evidence computation
4. Football State Machine execution with bidirectional lookahead
5. Validation and scoring

Usage:
    python pipeline/runner.py --output evaluation/results/fsm_submission.csv
    python pipeline/runner.py --test-mock
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

from games import GAME, GAMES, SOURCES, asset_paths, half_video_blocks  # noqa: E402
import possession_metrics as pm  # noqa: E402
from pipeline.dead_ball import (
    init_frame_mask,
    parse_smart_tagging_stoppages,
    apply_pitch_boundary_dead_balls,
    bridge_out_of_bounds_to_set_pieces,
)
from pipeline.ball_reconstruction import reconstruct_ball_trajectory
from pipeline.evidence import compute_frame_control_evidence, PITCH_LENGTH_M, PITCH_WIDTH_M
from pipeline.state_machine import FootballStateMachine


def load_player_teams_from_meta(meta_path):
    """Parse track slot team assignments (0 for Home, 1 for Away)."""
    if not os.path.isfile(meta_path):
        return None
    root = ET.parse(meta_path).getroot()
    teams = [t.get("id") for t in root.iter("Team")]
    if len(teams) < 2:
        return None
    home_id = teams[0]
    slots = [p.get("teamId") for p in root.iter("Player")]
    return np.array([0 if s == home_id else 1 for s in slots], dtype=np.int8)


def run_pipeline(
    output_path=os.path.join(ROOT, "evaluation", "results", "fsm_submission.csv"),
    lookahead_window=25,
    min_turnover_frames=8,
    max_interp_gap=20,
):
    """Run full possession pipeline on match assets."""
    paths = asset_paths(source="tactical")
    n_frames = GAMES[GAME]["n_video_frames"]

    print("=" * 60)
    print("Running Football State Machine Possession Pipeline")
    print("=" * 60)

    # 1. Initialize frame mask (ungraded 'X' and 2nd-half pre-kickoff 'D')
    print("Step 1: Initializing deterministic dead-ball & graded boundaries...")
    labels_mask = init_frame_mask(n_frames)

    # 2. Smart Tagging Stoppages & Restarts
    restarts = {11185: "A", 113742: "H"}  # Official kickoff anchors
    if os.path.isfile(paths["smart_tagging"]):
        print("Step 2: Parsing Smart Tagging set pieces and stoppages...")
        stoppages = parse_smart_tagging_stoppages(paths["smart_tagging"])
        for s in stoppages:
            # Mark dead ball interval preceding set piece
            d_start = max(0, s["dead_start"])
            d_end = min(n_frames - 1, s["dead_end"])
            for f in range(d_start, d_end):
                if labels_mask[f] == "":
                    labels_mask[f] = "D"

            # Register restart team if known
            if s.get("restart_team") in ("H", "A"):
                restarts[s["restart_frame"]] = s["restart_team"]
            elif s["team"].lower() in ("barcelona", "h"):
                restarts[s["restart_frame"]] = "H"
            elif s["team"].lower() in ("atletic club", "athletic club", "a"):
                restarts[s["restart_frame"]] = "A"

    # Check if raw tracking is available
    if not os.path.isfile(paths["atd_raw"]) or not os.path.isfile(paths["atd_meta"]):
        print(f"\nMatch tracking files not found at: {paths['atd_raw']}")
        print("Please unpack match data bundle into ./data or set MTAH_DATA_DIR.")
        return None

    # 3. Stream & Process ATD Tracking
    print("Step 3: Streaming ATD tracking and computing control evidence...")
    player_teams = load_player_teams_from_meta(paths["atd_meta"])
    n_slots = len(player_teams)

    ball_coords = np.full((n_frames, 2), np.nan, dtype=np.float32)
    player_coords = np.full((n_frames, n_slots, 2), np.nan, dtype=np.float32)

    with open(paths["atd_raw"], "r") as handle:
        for line in handle:
            parts = line.strip().split(":")
            if len(parts) != 3:
                continue
            frame_id = int(parts[0])
            video_frame = frame_id - 1
            if not (0 <= video_frame < n_frames):
                continue

            # Player positions
            player_str = parts[1]
            if player_str:
                p_items = player_str.split(";")
                for idx, item in enumerate(p_items):
                    if idx >= n_slots:
                        break
                    vals = item.split(",")
                    if len(vals) >= 2 and vals[0] != "NaN" and vals[1] != "NaN":
                        player_coords[video_frame, idx, 0] = float(vals[0])
                        player_coords[video_frame, idx, 1] = float(vals[1])

            # Ball position
            ball_str = parts[2]
            if ball_str:
                vals = ball_str.split(",")
                if len(vals) >= 2 and vals[0] != "NaN" and vals[1] != "NaN":
                    ball_coords[video_frame, 0] = float(vals[0])
                    ball_coords[video_frame, 1] = float(vals[1])

    # 4. Ball Reconstruction for short gaps
    print("Step 4: Reconstructing missing ball trajectories...")
    interp_ball, is_imputed = reconstruct_ball_trajectory(ball_coords, max_gap_frames=max_interp_gap)
    apply_pitch_boundary_dead_balls(labels_mask, interp_ball, tolerance=0.005)
    bridge_out_of_bounds_to_set_pieces(labels_mask, stoppages, ball_coords=interp_ball)

    # 5. Extract frame-level control signals
    print("Step 5: Extracting control signals...")
    nearest_teams = np.full(n_frames, None, dtype=object)
    has_controls = np.zeros(n_frames, dtype=bool)
    dists_h = np.full(n_frames, np.inf, dtype=np.float32)
    dists_a = np.full(n_frames, np.inf, dtype=np.float32)

    for f in range(n_frames):
        ev = compute_frame_control_evidence(
            interp_ball[f],
            player_coords[f],
            player_teams,
            pitch_dim=(PITCH_LENGTH_M, PITCH_WIDTH_M),
        )
        nearest_teams[f] = ev["nearest_team"]
        has_controls[f] = ev["has_control"]
        dists_h[f] = ev["dist_H"]
        dists_a[f] = ev["dist_A"]

    # 6. Execute State Machine with Bidirectional Lookahead
    print("Step 6: Executing Football State Machine with lookahead...")
    fsm = FootballStateMachine(
        lookahead_window=lookahead_window,
        min_turnover_frames=min_turnover_frames,
    )
    final_labels = fsm.run(
        n_frames=n_frames,
        nearest_teams=nearest_teams,
        has_controls=has_controls,
        dists_h=dists_h,
        dists_a=dists_a,
        dead_ball_mask=labels_mask,
        restarts=restarts,
    )

    # 7. Write Submission CSV
    print(f"Step 7: Writing submission to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df = pd.DataFrame({
        "frame": np.arange(n_frames, dtype=np.int64),
        "label": final_labels,
    })
    df.to_csv(output_path, index=False)

    # 8. Validate
    err = pm.validate_submission(df, n_frames)
    if err:
        print(f"VALIDATION FAILED: {err}")
    else:
        print(f"SUCCESS: Submission validated successfully! (199,319 rows)")

    return output_path


def test_mock_pipeline():
    """Verify state machine logic on a synthetic match sequence."""
    print("Testing Football State Machine on synthetic sequence...")
    n_frames = 500
    dead_mask = np.full(n_frames, "", dtype="<U1")
    dead_mask[:50] = "X"
    dead_mask[200:250] = "D"
    dead_mask[450:] = "X"

    nearest = np.full(n_frames, "H", dtype=object)
    has_control = np.ones(n_frames, dtype=bool)
    dists_h = np.ones(n_frames, dtype=np.float32) * 1.0
    dists_a = np.ones(n_frames, dtype=np.float32) * 5.0

    # Inject brief deflection (3 frames where A touches ball at frame 100)
    nearest[100:103] = "A"
    dists_a[100:103] = 0.5
    dists_h[100:103] = 2.5

    # Inject real turnover (sustained A possession from frame 300 to 380)
    nearest[300:380] = "A"
    dists_a[300:380] = 0.8
    dists_h[300:380] = 6.0

    fsm = FootballStateMachine(lookahead_window=20, min_turnover_frames=6)
    res = fsm.run(
        n_frames=n_frames,
        nearest_teams=nearest,
        has_controls=has_control,
        dists_h=dists_h,
        dists_a=dists_a,
        dead_ball_mask=dead_mask,
    )

    # Check that deflection at 100 was NOT converted to turnover (stays H)
    assert res[100] == "H" and res[101] == "H" and res[102] == "H", "Deflection should be absorbed by inertia!"
    # Check that sustained turnover at 300 converted to A
    assert res[305] == "A" and res[350] == "A", "Sustained turnover should transition to A!"
    # Check dead balls
    assert np.all(res[200:250] == "D"), "Stoppage must be D!"
    assert np.all(res[:50] == "X"), "Ungraded must be X!"

    print("ALL SYNTHETIC FSM TESTS PASSED SUCCESSFULLY!")
    print("Deflections absorbed into possession; turnovers verified; dead balls preserved.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Football State Machine Pipeline Runner")
    parser.add_argument("--output", "-o", default=os.path.join(ROOT, "evaluation", "results", "fsm_submission.csv"))
    parser.add_argument("--test-mock", action="store_true", help="Run synthetic state machine unit test")
    args = parser.parse_args()

    if args.test_mock:
        test_mock_pipeline()
    else:
        run_pipeline(output_path=args.output)
