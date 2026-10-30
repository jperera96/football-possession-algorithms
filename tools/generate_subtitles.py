"""Generate an .srt subtitle overlay for BAR-ATH_tactical.mp4 from a submission CSV.

When placed alongside `data/tactical/BAR-ATH_tactical.mp4` as `BAR-ATH_tactical.srt`,
video players (VLC, MPV, PotPlayer, Windows Media Player) automatically load and
display the live possession state, spell ID, frame counter, match clock, and
kinematic telemetry (ball speed, nearest player distances, collective player speed).

Usage:
    python tools/generate_subtitles.py --submission evaluation/results/football_engine.csv
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from run_experiment import build_match_context


def format_srt_time(frame_idx: int, fps: int = 25) -> str:
    """Convert a 25fps video frame index to SRT timestamp HH:MM:SS,mmm."""
    total_ms = int(round((frame_idx / fps) * 1000))
    hours = total_ms // 3600000
    rem = total_ms % 3600000
    minutes = rem // 60000
    rem = rem % 60000
    seconds = rem // 1000
    ms = rem % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def format_match_clock(frame_idx: int, fps: int = 25) -> str:
    """Format human-readable match clock relative to 1st/2nd half kickoffs."""
    if frame_idx < 11185:
        return "PRE-MATCH"
    elif frame_idx <= 90651:
        sec = (frame_idx - 11185) // fps
        return f"1H {sec // 60:02d}:{sec % 60:02d}"
    elif frame_idx <= 110807:
        return "HALFTIME"
    elif frame_idx < 113742:
        return "2H PRE-KO (Graded D)"
    elif frame_idx <= 190197:
        sec = 45 * 60 + (frame_idx - 113742) // fps
        return f"2H {sec // 60:02d}:{sec % 60:02d}"
    else:
        return "POST-MATCH"


def generate_srt(submission_path: str, output_path: str, step_frames: int = 12):
    df = pd.read_csv(submission_path)
    labels = df["label"].values.astype("<U1")
    n_frames = len(labels)

    ctx = build_match_context()
    scale = np.array([ctx.pitch_dim[0], ctx.pitch_dim[1]], dtype=np.float32)
    ball_m = ctx.ball_coords * scale
    players_m = ctx.player_coords * scale

    b_speed = np.zeros(n_frames, dtype=np.float32)
    b_diffs = np.diff(ball_m, axis=0)
    b_speed[1:] = np.sqrt(np.sum(b_diffs**2, axis=-1)) * 25.0

    diffs_p = players_m[1:] - players_m[:-1]
    v_players = np.sqrt(np.sum(diffs_p**2, axis=-1)) * 25.0
    with np.errstate(all="ignore"):
        median_speed = np.nanmedian(v_players, axis=1)
    k = np.ones(25, dtype=np.float32) / 25.0
    smooth_speed = np.zeros(n_frames, dtype=np.float32)
    smooth_speed[1:] = np.convolve(np.nan_to_num(median_speed, nan=1.5), k, mode="same")

    # Load public GT if available for comparison in first 5 minutes
    gt_path = os.path.join(ROOT, "evaluation", "gt", "BAR-ATH_possession_gt_public.csv")
    gt_labels = None
    if os.path.isfile(gt_path):
        gt_df = pd.read_csv(gt_path)
        gt_labels = gt_df["label"].values.astype("<U1")

    # Precompute contiguous segments and possession spell numbers
    segments = []
    i = 0
    spell_idx = 0
    prev_live_team = None
    while i < n_frames:
        start = i
        val = labels[i]
        while i < n_frames and labels[i] == val:
            i += 1
        end = i
        if val in ("H", "A"):
            if val != prev_live_team:
                spell_idx += 1
                prev_live_team = val
            cur_spell = spell_idx
        else:
            cur_spell = None
            if val == "X":
                prev_live_team = None
        segments.append((start, end, val, cur_spell))

    # Map set-piece tags by frame proximity
    sp_tags = {}
    if ctx.smart_tagging_stoppages:
        for s in ctx.smart_tagging_stoppages:
            rf = s["restart_frame"]
            desc = f"{s.get('type', s.get('code'))} ({s.get('restart_team', '')})"
            for f in range(max(0, rf - 50), min(n_frames, rf + 150)):
                sp_tags[f] = desc

    # Build SRT cues (subdivided every `step_frames` within each segment so telemetry updates live,
    # while always snapping exactly to segment transition frames!)
    lines = []
    cue_idx = 1

    team_display = {
        "H": '<font color="#4da6ff"><b>[H] BARCELONA</b></font>',
        "A": '<font color="#ff4d4d"><b>[A] ATHLETIC CLUB</b></font>',
        "D": '<font color="#ffd11a"><b>[D] DEAD BALL / STOPPAGE</b></font>',
        "X": '<font color="#999999"><b>[X] UNGRADED</b></font>',
    }

    for seg_start, seg_end, val, cur_spell in segments:
        seg_dur_s = (seg_end - seg_start) / 25.0
        if cur_spell is not None:
            seg_header = f"{team_display[val]} | Spell #{cur_spell:03d} ({seg_dur_s:.1f}s) [{seg_start}..{seg_end}]"
        else:
            seg_header = f"{team_display[val]} ({seg_dur_s:.1f}s) [{seg_start}..{seg_end}]"

        t = seg_start
        while t < seg_end:
            t_next = min(seg_end, t + step_frames)
            mid_f = (t + t_next) // 2

            # Compute nearest H and A distances at mid_f
            b = ball_m[mid_f]
            if not np.isnan(b[0]):
                p = players_m[mid_f]
                v = ~np.isnan(p[:, 0])
                if np.any(v):
                    dists = np.sqrt(np.sum((p[v] - b) ** 2, axis=1))
                    tms = ctx.player_teams[v].copy()
                    v_slots = np.flatnonzero(v)
                    for idx_s, s_id in enumerate(v_slots):
                        if s_id in (23, 45):
                            px = p[s_id, 0]
                            if mid_f <= 90651:
                                tms[idx_s] = 0 if px < 52.5 else 1
                            elif mid_f >= 110808:
                                tms[idx_s] = 0 if px > 52.5 else 1
                    dh = np.min(dists[tms == 0]) if np.any(tms == 0) else 99.0
                    da = np.min(dists[tms == 1]) if np.any(tms == 1) else 99.0
                    ball_str = f"Ball: ({b[0]:.0f},{b[1]:.0f})m {b_speed[mid_f]:.1f}m/s | dH={dh:.1f}m dA={da:.1f}m"
                else:
                    ball_str = f"Ball: ({b[0]:.0f},{b[1]:.0f})m {b_speed[mid_f]:.1f}m/s"
            else:
                ball_str = "Ball: NaN (Occluded/Out)"

            gt_info = ""
            if gt_labels is not None and gt_labels[mid_f] != "X":
                g_val = gt_labels[mid_f]
                match_sym = "OK" if g_val == val else f"MISMATCH(GT={g_val})"
                gt_info = f" | PublicGT: {match_sym}"

            tag_info = f" | Tag: {sp_tags[mid_f]}" if mid_f in sp_tags else ""
            clock_str = format_match_clock(t)
            line2 = f"Frame: {t} ({clock_str}) | {ball_str} | PlrSpd: {smooth_speed[mid_f]:.1f}m/s{gt_info}{tag_info}"

            lines.append(f"{cue_idx}\n{format_srt_time(t)} --> {format_srt_time(t_next)}\n{seg_header}\n{line2}\n")
            cue_idx += 1
            t = t_next

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated {cue_idx - 1} subtitle cues -> {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SRT subtitles for tactical video inspection.")
    parser.add_argument(
        "--submission",
        default=os.path.join(ROOT, "evaluation", "results", "football_engine.csv"),
        help="Path to submission CSV",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(ROOT, "data", "tactical", "BAR-ATH_tactical.srt"),
        help="Output .srt file path (defaults to data/tactical/BAR-ATH_tactical.srt for auto-loading)",
    )
    parser.add_argument(
        "--step-frames",
        type=int,
        default=12,
        help="Telemetry refresh interval in frames (default: 12 frames = 0.48s)",
    )
    args = parser.parse_args()
    generate_srt(args.submission, args.output, args.step_frames)
