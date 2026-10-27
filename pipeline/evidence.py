"""Extraction of spatial and kinematic possession evidence from tracking data.

Converts normalized pitch coordinates to metric distances (105.3m x 68.0m),
computes distances to nearest Home and Away players, and evaluates instantaneous
control likelihoods.
"""

import numpy as np

# Real pitch dimensions for BAR-ATH
PITCH_LENGTH_M = 105.3
PITCH_WIDTH_M = 68.0

# Typical football control radii (in metres)
CONTROL_RADIUS_M = 2.0
CONTESTED_DELTA_M = 0.8


def compute_frame_control_evidence(
    ball_pos,
    player_positions,
    player_teams,
    pitch_dim=(PITCH_LENGTH_M, PITCH_WIDTH_M),
    control_radius=CONTROL_RADIUS_M,
):
    """Compute instantaneous control evidence for a single frame.

    Args:
        ball_pos: (2,) array [x, y] in normalized (0..1) coords, or NaNs
        player_positions: (N_slots, 2) array [x, y] in normalized coords, or NaNs
        player_teams: (N_slots,) array with 0 (Home) or 1 (Away)
        pitch_dim: (length_m, width_m)
        control_radius: Maximum distance (m) to consider a player in control

    Returns:
        dict: {
            'dist_H': min distance to Home player in meters (or inf),
            'dist_A': min distance to Away player in meters (or inf),
            'nearest_team': 'H', 'A', or None,
            'has_control': bool,
            'is_contested': bool
        }
    """
    if np.isnan(ball_pos[0]) or np.isnan(ball_pos[1]):
        return {
            "dist_H": float("inf"),
            "dist_A": float("inf"),
            "nearest_team": None,
            "has_control": False,
            "is_contested": False,
        }

    # Scale to metric pitch coordinates
    scale = np.array([pitch_dim[0], pitch_dim[1]])
    ball_m = ball_pos * scale
    players_m = player_positions * scale

    # Valid player slots
    valid_players = ~np.isnan(players_m[:, 0]) & ~np.isnan(players_m[:, 1])
    if not np.any(valid_players):
        return {
            "dist_H": float("inf"),
            "dist_A": float("inf"),
            "nearest_team": None,
            "has_control": False,
            "is_contested": False,
        }

    diffs = players_m[valid_players] - ball_m
    dists = np.sqrt(np.sum(diffs**2, axis=1))
    teams = player_teams[valid_players]

    mask_h = teams == 0
    mask_a = teams == 1

    min_h = np.min(dists[mask_h]) if np.any(mask_h) else float("inf")
    min_a = np.min(dists[mask_a]) if np.any(mask_a) else float("inf")

    if min_h < min_a:
        nearest = "H"
        closest_dist = min_h
        dist_diff = min_a - min_h
    elif min_a < min_h:
        nearest = "A"
        closest_dist = min_a
        dist_diff = min_h - min_a
    else:
        nearest = None
        closest_dist = min_h
        dist_diff = 0.0

    has_control = closest_dist <= control_radius
    is_contested = dist_diff < CONTESTED_DELTA_M

    return {
        "dist_H": min_h,
        "dist_A": min_a,
        "nearest_team": nearest,
        "has_control": has_control,
        "is_contested": is_contested,
    }
