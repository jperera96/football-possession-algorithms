"""Dead-ball and stoppage interval detection.

Demarcates all non-possession frames ('D' and 'X'):
1. Ungraded intervals (< 11185, halftime 90652..110807, > 190197) marked as 'X'.
2. Pre-kickoff 2nd half window (110808..113741) marked strictly as 'D'.
3. Smart Tagging set pieces and stoppage windows.
4. Pitch boundary crossings (ball outside [0, 1] x [0, 1]).
"""

import os
import sys
import xml.etree.ElementTree as ET
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from games import GAME, GAMES, half_video_blocks


# Known fixed boundaries in video frames (25 fps)
UNGRADED_PRE_MATCH = (0, 11184)
FIRST_HALF = (11185, 90651)
HALFTIME = (90652, 110807)
SECOND_HALF_PRE_KICKOFF = (110808, 113741)  # All graded as 'D'!
SECOND_HALF_PLAY = (113742, 190197)
UNGRADED_POST_MATCH = (190198, 199318)


def init_frame_mask(n_frames=199319):
    """Initialize frame labels with deterministic graded/ungraded boundaries.

    Returns:
        labels: np.ndarray of shape (n_frames,), dtype='<U1'
                Populated with 'X' for ungraded and 'D' for 2nd half pre-kickoff.
    """
    labels = np.full(n_frames, "", dtype="<U1")

    # Ungraded frames -> 'X'
    labels[UNGRADED_PRE_MATCH[0] : UNGRADED_PRE_MATCH[1] + 1] = "X"
    labels[HALFTIME[0] : HALFTIME[1] + 1] = "X"
    labels[UNGRADED_POST_MATCH[0] : UNGRADED_POST_MATCH[1] + 1] = "X"

    # 2nd half pre-kickoff -> Graded 'D'
    labels[SECOND_HALF_PRE_KICKOFF[0] : SECOND_HALF_PRE_KICKOFF[1] + 1] = "D"

    return labels


def parse_smart_tagging_stoppages(xml_path, fps=25, pre_restart_sec=3.0):
    """Extract dead-ball intervals and restart events from Smart Tagging XML.

    - Set pieces mark the restart of play. The period immediately preceding
      the restart execution (pre_restart_sec) is a dead-ball stoppage ('D').
    - Goals induce a dead-ball stoppage for the duration of celebrations from
      the goal frame until the kickoff after the goal.

    Args:
        xml_path: Path to BAR-ATH_tactical_smart_tagging.xml
        fps: Frames per second (25)
        pre_restart_sec: Duration in seconds prior to set piece execution considered dead ball

    Returns:
        List of dicts: [{'code': str, 'type': str, 'team': str, 'restart_frame': int, 'dead_start': int, 'dead_end': int, 'restart_team': str}]
    """
    if not os.path.isfile(xml_path):
        return []

    tree = ET.parse(xml_path)
    root = tree.getroot()
    stoppages = []

    for instance in root.iter("instance"):
        code = (instance.findtext("code") or "").strip().lower()
        start_s = float(instance.findtext("start") or 0.0)
        end_s = float(instance.findtext("end") or 0.0)

        tags = {}
        for label in instance.findall("label"):
            group = (label.findtext("group") or "").strip()
            text = (label.findtext("text") or "").strip()
            if group:
                tags[group.lower()] = text

        if code == "goals":
            # Goal celebration stoppage: dead from goal until subsequent kickoff
            dead_start = int(round(start_s * fps))
            dead_end = int(round(end_s * fps))
            restart_frame = dead_end
            
            # Kickoff taken by the conceding team
            scorer_team = tags.get("team", "").lower()
            if "barcelona" in scorer_team or scorer_team == "h":
                restart_team = "A"  # Barcelona scored -> Athletic restarts
            elif "atletic" in scorer_team or "athletic" in scorer_team or scorer_team == "a":
                restart_team = "H"  # Athletic scored -> Barcelona restarts
            else:
                restart_team = "N/A"

            stoppages.append({
                "code": code,
                "type": "goal_celebration",
                "team": tags.get("team", "N/A"),
                "restart_frame": restart_frame,
                "dead_start": dead_start,
                "dead_end": dead_end,
                "restart_team": restart_team,
            })

        elif code == "set pieces":
            # The set piece execution marks the restart
            restart_frame = int(round(start_s * fps))
            dead_start = max(0, restart_frame - int(round(pre_restart_sec * fps)))
            dead_end = restart_frame  # Play resumes at restart_frame, not 35s later!

            team_tag = tags.get("team", "N/A").lower()
            if "barcelona" in team_tag or team_tag == "h":
                restart_team = "H"
            elif "atletic" in team_tag or "athletic" in team_tag or team_tag == "a":
                restart_team = "A"
            else:
                restart_team = "N/A"

            stoppages.append({
                "code": code,
                "type": tags.get("type", "unknown"),
                "team": tags.get("team", "N/A"),
                "restart_frame": restart_frame,
                "dead_start": dead_start,
                "dead_end": dead_end,
                "restart_team": restart_team,
            })

    return stoppages


def apply_pitch_boundary_dead_balls(labels, ball_coords, tolerance=0.005):
    """Mark frames where the ball is clearly out of pitch bounds as 'D'.

    Args:
        labels: Frame label array to update in-place
        ball_coords: np.ndarray of shape (N, 2), normalized coordinates (0..1)
        tolerance: Coordinate margin outside [0, 1] before declaring out of bounds
    """
    valid_coords = ~np.isnan(ball_coords[:, 0]) & ~np.isnan(ball_coords[:, 1])
    out_of_bounds = (
        (ball_coords[:, 0] < -tolerance)
        | (ball_coords[:, 0] > 1.0 + tolerance)
        | (ball_coords[:, 1] < -tolerance)
        | (ball_coords[:, 1] > 1.0 + tolerance)
    )

    # Only apply where frame is not already designated ungraded ('X')
    mask = valid_coords & out_of_bounds & (labels == "")
    labels[mask] = "D"
    return labels


def bridge_out_of_bounds_to_set_pieces(labels, stoppages, max_gap_sec=30.0, fps=25):
    """Bridge dead ball from an out-of-bounds event to the ensuing set-piece restart.

    When the ball goes out of play (e.g. over the end line for a goal kick or corner),
    play remains dead while players reposition and set the ball down.

    Args:
        labels: Frame label array to update in-place
        stoppages: List of stoppage dicts from parse_smart_tagging_stoppages
        max_gap_sec: Maximum lookback window to bridge out-of-bounds frames to the restart
        fps: Frames per second
    """
    max_gap_frames = int(round(max_gap_sec * fps))
    set_pieces = sorted(
        [s for s in stoppages if s.get("code") == "set pieces"],
        key=lambda x: x["restart_frame"],
    )
    prev_restart_f = 0
    for s in set_pieces:
        restart_f = s["restart_frame"]
        # Never look back across a previous set piece's restart and initial execution window
        search_start = max(prev_restart_f + 150, restart_f - max_gap_frames)
        if search_start < restart_f:
            d_indices = np.where(labels[search_start:restart_f] == "D")[0]
            if len(d_indices) > 0:
                first_d = search_start + d_indices[0]
                for f in range(first_d, restart_f):
                    if labels[f] == "":
                        labels[f] = "D"
        prev_restart_f = restart_f
    return labels


def resolve_throw_in_restart_teams(stoppages, player_coords, player_teams, n_frames, setup_window=50):
    """Deterministically determine the team taking each throw-in from sideline positioning.

    At a throw-in, the thrower stands at or just outside the touchline,
    while all other players remain inside the pitch.

    Returns:
        dict: {restart_frame: 'H' or 'A'} for all resolved throw-ins.
    """
    restarts = {}
    for s in stoppages:
        if s.get("code") == "set pieces" and s.get("type", "").lower() == "throw-in":
            f = s["restart_frame"]
            low = max(0, f - setup_window)
            high = min(n_frames, f + setup_window)
            p_y = player_coords[low:high, :, 1]
            dist_sideline = np.minimum(np.abs(p_y), np.abs(1.0 - p_y))
            with np.errstate(all="ignore"):
                min_dist_to_line = np.nanmin(dist_sideline, axis=0)
            if not np.all(np.isnan(min_dist_to_line)):
                best_slot = np.nanargmin(min_dist_to_line)
                team = "H" if player_teams[best_slot] == 0 else "A"
                restarts[f] = team
    return restarts
