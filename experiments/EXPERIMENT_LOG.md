# Strategy Experiment Log & Benchmark Board

| Timestamp | Strategy / File | spellF1 | macroF1 | Poss | Dur(s) | Frag | Notes |
|---|---|---|---|---|---|---|---|
| 2026-10-28 15:58:30 | `fsm_lookahead.csv` | **0.2455** | 0.6697 | 27 | 9.2 | 1.38 | First run of FSM with lookahead on real tracking data |
| 2026-10-28 15:58:46 | `baseline_smooth50.csv` | **0.2900** | 0.6708 | 23 | 9.9 | 1.33 | Full benchmark suite across all strategies |
| 2026-10-28 15:58:48 | `baseline_smooth25.csv` | **0.2531** | 0.6464 | 32 | 7.1 | 1.76 | Full benchmark suite across all strategies |
| 2026-10-28 15:58:50 | `baseline_smooth125.csv` | **0.3733** | 0.6959 | 13 | 17.2 | 0.86 | Full benchmark suite across all strategies |
| 2026-10-28 15:58:52 | `baseline_raw.csv` | **0.0328** | 0.6169 | 117 | 2.0 | 5.86 | Full benchmark suite across all strategies |
| 2026-10-28 15:58:56 | `fsm_lookahead.csv` | **0.2455** | 0.6697 | 27 | 9.2 | 1.38 | Full benchmark suite across all strategies |
| 2026-10-28 15:59:00 | `ablation_no_lookahead.csv` | **0.1524** | 0.6739 | 46 | 5.4 | 2.29 | Full benchmark suite across all strategies |
| 2026-10-28 15:59:04 | `ablation_no_deadball.csv` | **0.2455** | 0.6697 | 27 | 9.2 | 1.38 | Full benchmark suite across all strategies |
| 2026-10-28 15:59:07 | `hmm_viterbi.csv` | **0.0083** | 0.5554 | 79 | 1.9 | 7.24 | Full benchmark suite across all strategies |
| 2026-10-28 16:07:27 | `fsm_advanced.csv` | **0.2100** | 0.6559 | 23 | 10.0 | 1.33 | FSM Advanced: 50f lookahead, dead-ball absence detector, micro-spell merging |
| 2026-10-28 16:08:45 | `fsm_hysteresis.csv` | **0.3053** | 0.6686 | 21 | 11.4 | 1.24 | Inertia-Hysteresis State Machine (window 40, barrier 15) |
| 2026-10-28 16:24:45 | `football_engine.csv` | **0.2769** | 0.6774 | 22 | 10.8 | 1.29 | FootballEngine: W55, Barrier12, DW40 with kickoff anchors |
| 2026-10-28 16:25:24 | `football_engine.csv` | **0.3294** | 0.6886 | 17 | 14.0 | 1.05 | FootballEngine default config (W60, b12, dw35) -> 17 possessions, 14.0s dur, 0.3294 spellF1 |
| 2026-10-28 16:51:44 | `football_engine.csv` | **0.4571** | 0.7383 | 18 | 14.6 | 1.1 | FootballEngine with restart anchoring and out-of-bounds bridging |
| 2026-10-29 19:46:52 | `football_engine.csv` | **0.5333** | 0.7820 | 19 | 14.1 | 1.19 | FootballEngine with Control Radius (3m) and Kinematic Aerial Stoppage Gating |
| 2026-10-29 20:18:04 | `football_engine.csv` | **0.6057** | 0.8528 | 18 | 13.7 | 1.19 |  |
| 2026-10-29 20:41:36 | `football_engine.csv` | **0.6057** | 0.8539 | 18 | 13.7 | 1.19 |  |
| 2026-10-30 09:59:22 | `football_engine.csv` | **0.6424** | 0.8591 | 16 | 15.4 | 1.1 |  |
| 2026-10-30 10:35:08 | `football_engine.csv` | **0.7097** | 0.8907 | 14 | 17.2 | 1.0 |  |
| 2026-10-30 10:36:04 | `football_engine.csv` | **0.7636** | 0.8915 | 16 | 15.0 | 1.1 |  |
| 2026-10-30 11:38:33 | `football_engine.csv` | **0.8667** | 0.9552 | 13 | 18.8 | 0.81 | v7 first-principles audit: GK slot disambiguation, set-piece stationary ball wait, GOALS build-up preservation, 4-way symmetric clearances with velocity-apex extension and inertia-lag bridging, kinematic pre-dead split, and unverified occlusion bridging |
| 2026-10-30 12:12:10 | `football_engine.csv` | **0.8667** | 0.9617 | 13 | 18.7 | 0.81 | v8 full-match set-piece audit: fix 30s consecutive set-piece bridge overwrite (recovering 7 full-match possessions / 106.8s of live play), extend delayed set-piece NaN/OOB wait to 320f, and verify Throw-in (Team: N/A) restart teams against post-throw ball control |
| 2026-10-30 12:35:51 | `football_engine.csv` | **0.9375** | 0.9695 | 15 | 16.2 | 0.9 |  |
| 2026-10-30 12:54:57 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
| 2026-10-30 13:21:18 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
| 2026-10-30 13:54:44 | `football_engine.csv` | **0.9000** | 0.9599 | 15 | 16.5 | 0.9 | v12: Fix touchline grazes, live-play OOB bridging, and early-tagged set-piece pre-rolls (21286..21611, 125000..125148, 163527..163736) |
| 2026-10-30 13:56:17 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 | v12: Fix touchline grazes, live-play OOB bridging, and early-tagged set-piece pre-rolls (21286..21611, 125000..125148, 163527..163736) |
| 2026-10-30 14:20:45 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
| 2026-10-30 14:36:39 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
| 2026-10-30 14:45:28 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
| 2026-10-30 15:09:15 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
| 2026-10-30 15:31:28 | `football_engine.csv` | **0.9375** | 0.9730 | 15 | 16.3 | 0.9 |  |
