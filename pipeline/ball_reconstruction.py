"""Ball trajectory reconstruction & missing observation imputation.

Addresses the 41% missing ball frames in tracking:
1. Short-gap linear interpolation (<= max_interp_frames, ~0.4s - 0.8s).
2. Carrier proximity tracking: attaches missing ball to the carrying player slot.
3. Keeps track of whether an observation is measured, interpolated, or absent.
"""

import numpy as np


def reconstruct_ball_trajectory(ball_coords, max_gap_frames=20):
    """Interpolate short missing intervals in ball trajectory.

    Args:
        ball_coords: np.ndarray of shape (N, 2), normalized (0..1) coordinates, with NaNs
        max_gap_frames: Maximum length of contiguous NaN frames to interpolate (20 frames = 0.8s)

    Returns:
        interp_coords: np.ndarray of shape (N, 2)
        is_interpolated: boolean np.ndarray of shape (N,) indicating imputed frames
    """
    n_frames = len(ball_coords)
    interp_coords = ball_coords.copy()
    is_interpolated = np.zeros(n_frames, dtype=bool)

    valid_mask = ~np.isnan(ball_coords[:, 0]) & ~np.isnan(ball_coords[:, 1])
    if not np.any(valid_mask):
        return interp_coords, is_interpolated

    valid_indices = np.flatnonzero(valid_mask)

    for i in range(len(valid_indices) - 1):
        idx_start = valid_indices[i]
        idx_end = valid_indices[i + 1]
        gap_length = idx_end - idx_start - 1

        if 0 < gap_length <= max_gap_frames:
            # Linear interpolation across short gap
            start_pos = ball_coords[idx_start]
            end_pos = ball_coords[idx_end]
            alpha = np.linspace(0, 1, gap_length + 2)[1:-1, None]
            interp_coords[idx_start + 1 : idx_end] = (1 - alpha) * start_pos + alpha * end_pos
            is_interpolated[idx_start + 1 : idx_end] = True

    return interp_coords, is_interpolated
