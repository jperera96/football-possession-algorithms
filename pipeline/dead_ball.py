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
    """Extract dead-ball intervals from Smart Tagging XML.

    Set pieces mark the restart of play. The period immediately preceding
    the restart execution (pre_restart_sec) is a dead ball stoppage ('D').

    Args:
        xml_path: Path to BAR-ATH_tactical_smart_tagging.xml
        fps: Frames per second (25)
        pre_restart_sec: Duration in seconds prior to set piece execution considered dead ball

    Returns:
        List of dicts: [{'type': str, 'team': str, 'restart_frame': int, 'dead_start': int, 'dead_end': int}]
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

        if code in ("set pieces", "goals"):
            restart_frame = int(round(start_s * fps))
            dead_start = max(0, restart_frame - int(round(pre_restart_sec * fps)))
            dead_end = int(round(end_s * fps))

            stoppages.append({
                "code": code,
                "type": tags.get("type", "unknown"),
                "team": tags.get("team", "N/A"),
                "restart_frame": restart_frame,
                "dead_start": dead_start,
                "dead_end": dead_end,
            })

    return stoppages


def apply_pitch_boundary_dead_balls(labels, ball_coords, tolerance=0.02):
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
