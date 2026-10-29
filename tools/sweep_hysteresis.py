"""Systematic parameter sensitivity analysis for Inertia-Hysteresis State Machine."""

import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "evaluation"))

from strategies.fsm_hysteresis import FSMHysteresisStrategy
from run_experiment import build_match_context
import possession_metrics as pm

ctx = build_match_context()
gt_codes = pm.label_codes(pm.read_label_csv(os.path.join(ROOT, "evaluation", "gt", "BAR-ATH_possession_gt_public.csv")))

print("=" * 70)
print(f"{'W':<4} {'Barrier':<8} {'DeadW':<6} | {'spellF1':<8} {'macroF1':<8} {'Poss':<5} {'Dur(s)':<6} {'Frag':<5}")
print("=" * 70)

results = []
for w in [30, 40, 50, 60]:
    for b in [8, 12, 16, 20]:
        for dw in [35, 50, 65]:
            strat = FSMHysteresisStrategy(window=w, turnover_barrier=b, dead_window=dw)
            preds = strat.predict(ctx)
            res = pm.evaluate(gt_codes, pm.label_codes(preds))
            sf1 = res['spell_f1_mean']
            mf1 = res['macro_f1']
            poss = res['n_pred_spells']
            dur = res['mean_spell_duration_s']
            frag = res['fragmentation']
            print(f"{w:<4} {b:<8} {dw:<6} | {sf1:<8.4f} {mf1:<8.4f} {poss:<5} {dur:<6.1f} {frag:<5.2f}")
            results.append({
                "w": w, "b": b, "dw": dw,
                "spellF1": sf1, "macroF1": mf1,
                "poss": poss, "dur": dur, "frag": frag
            })

df = pd.DataFrame(results)
best_spell = df.loc[df['spellF1'].idxmax()]
print("=" * 70)
print(f"Best spellF1 configuration:")
print(best_spell)
print("=" * 70)
