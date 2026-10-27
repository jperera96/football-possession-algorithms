"""Strategy Registry and discovery for More Than A Hack 2027.

Provides a unified interface to list, instantiate, and compare independent strategies.
"""

from typing import Dict, Type
from strategies.base import BaseStrategy
from strategies.baseline_window import BaselineWindowStrategy
from strategies.fsm_lookahead import FSMLookaheadStrategy
from strategies.fsm_ablation import FSMNoLookaheadStrategy, FSMNoDeadBallStrategy
from strategies.hmm_viterbi import HMMViterbiStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "baseline_smooth50": lambda **kw: BaselineWindowStrategy(window_half_width=50, **kw),
    "baseline_smooth25": lambda **kw: BaselineWindowStrategy(window_half_width=25, **kw),
    "baseline_smooth125": lambda **kw: BaselineWindowStrategy(window_half_width=125, **kw),
    "baseline_raw": lambda **kw: BaselineWindowStrategy(window_half_width=0, **kw),
    "fsm_lookahead": FSMLookaheadStrategy,
    "ablation_no_lookahead": FSMNoLookaheadStrategy,
    "ablation_no_deadball": FSMNoDeadBallStrategy,
    "hmm_viterbi": HMMViterbiStrategy,
}


def get_strategy(name: str, **kwargs) -> BaseStrategy:
    """Retrieve an instantiated strategy by name."""
    if name not in STRATEGY_REGISTRY:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise KeyError(f"Unknown strategy '{name}'. Available strategies: {available}")
    factory = STRATEGY_REGISTRY[name]
    return factory(**kwargs)


def list_strategies() -> Dict[str, str]:
    """Return dictionary of available strategy names and their descriptions."""
    out = {}
    for name in STRATEGY_REGISTRY:
        strat = get_strategy(name)
        out[name] = strat.description
    return out
