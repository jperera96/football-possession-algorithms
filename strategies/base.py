"""Base class and context definitions for independent possession strategies.

Every strategy adheres to the same interface:
1. Takes a `TrackingContext` (tracking coords, dead-ball mask, restarts, pitch dim).
2. Produces a 1D numpy array of exactly 199,319 labels ('H', 'A', 'D', 'X').
3. Exposes its hyperparameters for experiment logging.
4. Provides a `test_synthetic()` method for standalone unit verification.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np


@dataclass
class TrackingContext:
    """Preprocessed tracking and match context provided to strategies."""
    n_frames: int
    ball_coords: np.ndarray             # (n_frames, 2), normalized pitch coords (with NaNs)
    player_coords: np.ndarray           # (n_frames, n_slots, 2), normalized pitch coords
    player_teams: np.ndarray            # (n_slots,), 0 for Home, 1 for Away
    dead_ball_mask: np.ndarray          # (n_frames,), 'X', 'D', or ''
    restarts: Dict[int, str] = field(default_factory=dict)  # {frame_idx: 'H' or 'A'}
    smart_tagging_stoppages: List[Dict] = field(default_factory=list)
    pitch_dim: tuple = (105.3, 68.0)     # Real pitch dimensions (meters)


class BaseStrategy(ABC):
    """Abstract base class for all independent possession inference strategies."""

    def __init__(self, name: str, description: str, **params):
        self.name = name
        self.description = description
        self.params = params

    def get_params(self) -> Dict[str, Any]:
        """Return dict of strategy hyperparameters for experiment logging."""
        return self.params.copy()

    @abstractmethod
    def predict(self, ctx: TrackingContext) -> np.ndarray:
        """Run possession inference and return array of shape (n_frames,) with labels 'H', 'A', 'D', 'X'."""
        pass

    @abstractmethod
    def test_synthetic(self) -> bool:
        """Run synthetic unit test to verify strategy logic independently."""
        pass
