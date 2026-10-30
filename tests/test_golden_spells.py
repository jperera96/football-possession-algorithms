"""Golden-spell regression tests for the football_engine strategy.

Each case encodes a physical, human-verified observation made while watching the tactical
video with the predicted-possession subtitle overlay (see tools/generate_subtitles.py).
They assert *what physically happened* (who had the ball / was it dead) over a window that is
deliberately inset from the transition frames, so they are robust to few-frame latency changes
but fail if a whole spell is lost, split or mislabeled again.

Add one case here every time a new physical bug is reported and fixed.

Run:
    .\\.venv\\Scripts\\python.exe -m unittest tests.test_golden_spells -v
    .\\.venv\\Scripts\\python.exe tests/test_golden_spells.py

The tests skip themselves when the gated match data is not present (e.g. on CI).
"""

import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_PREDS = None
_SKIP_REASON = None


def _predictions():
    global _PREDS, _SKIP_REASON
    if _PREDS is not None or _SKIP_REASON is not None:
        return _PREDS
    try:
        from run_experiment import build_match_context
        from strategies.football_engine import FootballEngineStrategy

        ctx = build_match_context(use_cache=True)
        _PREDS = FootballEngineStrategy().predict(ctx)
    except Exception as exc:  # data missing / gated
        _SKIP_REASON = f"match data unavailable: {exc!r}"
    return _PREDS


class GoldenSpells(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.preds = _predictions()
        if cls.preds is None:
            raise unittest.SkipTest(_SKIP_REASON)

    def frac(self, a, b, label):
        seg = self.preds[a:b]
        return float(np.mean(seg == label))

    def assert_window(self, a, b, label, min_frac=0.95, why=""):
        got = self.frac(a, b, label)
        self.assertGreaterEqual(
            got,
            min_frac,
            f"[{a}..{b}) expected >= {min_frac:.0%} '{label}' but got {got:.1%} ({why})",
        )

    # --- Contract invariants -------------------------------------------------------------
    def test_contract_shape_and_abstentions(self):
        self.assertEqual(len(self.preds), 199319)
        self.assertTrue(set(np.unique(self.preds)) <= {"H", "A", "D", "X"})
        self.assertTrue(np.all(self.preds[:11185] == "X"), "pre-match must abstain")
        self.assertTrue(np.all(self.preds[90652:110808] == "X"), "halftime must abstain")
        self.assertTrue(np.all(self.preds[190198:] == "X"), "post-match must abstain")
        self.assertFalse(np.any(self.preds[11185:90652] == "X"), "1st half must be answered")
        self.assertFalse(np.any(self.preds[110808:190198] == "X"), "2nd half must be answered")

    def test_second_half_pre_kickoff_is_dead(self):
        self.assertTrue(np.all(self.preds[110808:113742] == "D"))

    # --- Human-reported physical cases ---------------------------------------------------
    def test_short_athletic_spell_11554(self):
        self.assert_window(11560, 11620, "A", why="short but clear Athletic possession")

    def test_kounde_serves_offside_free_kick_12963(self):
        # Original bug: stayed D until ~13005. Engine now switches to H at ~12979.
        self.assert_window(12985, 13000, "H", 1.0, "free kick already taken; must not stay D until 13005")

    @unittest.expectedFailure
    def test_kounde_free_kick_exact_kick_frame_12963(self):
        # Known remaining ~16f restart latency (kick at 12963, engine flips at ~12979).
        # When fixed this reports an 'unexpected success': tighten the test above and drop this marker.
        self.assert_window(12966, 12985, "H", 0.9, "H should start at the kicker's touch")

    def test_athletic_throw_in_with_occluded_ball_19670(self):
        self.assert_window(19680, 19780, "A", 0.9, "Athletic serving; not a dead ball")

    def test_no_false_dead_ball_during_live_play_21286(self):
        got = self.frac(21300, 21570, "D")
        self.assertLess(got, 0.05, f"live play mislabeled D ({got:.1%})")

    def test_deflection_does_not_flip_possession_23299(self):
        seg = self.preds[23100:23825]
        self.assertTrue(np.all(seg == "A"), "Barcelona deflection fly-by must not create an H spell")

    def test_goalkeeper_catch_and_hold_is_barcelona_23862(self):
        seg = self.preds[23830:24129]
        self.assertTrue(np.all(seg == "H"), "GK holding the ball must be H (not A, not D)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
