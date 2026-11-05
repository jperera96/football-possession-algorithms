# Technology review

Principle: Python 3.11, NumPy, pandas, an own temporal decoder, pytest, Ruff and uv, unless the code
shows a concrete need. It does not. Licences marked * come from general knowledge and must be
rechecked at adoption; others were checked on 2026-11-05 on PyPI or GitHub.

| Technology | In repo today | Would add | Real need | Integration | Maintenance | Risks | Licence | Class | Priority | Simpler alternative |
|---|---|---|---|---|---|---|---|---|---|---|
| Python 3.11 | Used in CI with 3.13; docs say 3.8+ | One target | Yes, `tomllib`, reproducibility | Low | Low | None | PSF* | CORE | P0 | None |
| NumPy | Yes, unpinned | Arrays | Yes | None | Low | Version changes results | BSD* | CORE | P0 | None |
| pandas | Yes, unpinned | CSV, scorer | Yes (scorer) | None | Low | Same | BSD* | CORE | P0 | None |
| Own Viterbi | Prototype | Decoder | Candidate | Low (~100 lines) | Low | Bugs; mitigated by tests | Repo | CORE if selected | P1 | FSM |
| pytest | No | Real tests | Yes | Low | Low | None | MIT* | CORE (dev) | P0 | unittest, used by governance |
| Ruff | Governance only | Lint | Yes | Low | Low | Noise on legacy code; scope it | MIT* | CORE (dev) | P0 | None |
| uv | No | Lockfile | Yes | Low | Low | One more tool; `requirements.txt` export stays as fallback | MIT/Apache* | CORE (dev) | P0 | pip-tools |
| GitHub Actions | Yes | CI | Yes | Done | Low | Private-repo limits | Service | CORE | P0 | None |
| kloppy | Starter only, pinned 3.18.0; latest 3.19.1 | EPTS and event loading | Adapters only | Low | Low | Keep out of submission path; pin to the starter's version unless a reason appears | BSD-3 | OPTIONAL | P1 | Own small parser |
| SciPy | No | Filters, stats | No concrete gap; bootstrap exists in the scorer | Low | Low | Bigger environment | BSD* | OPTIONAL | Only on need | NumPy |
| FilterPy | No | Kalman tools | No. A constant-velocity filter is short in NumPy, and the 2.0.0 release dated 2026-10-26 is too new to trust, after 1.4.5 from 2018 | Low | Unknown | API churn | MIT | REJECTED for phase 1 | n/a | Interpolation; own NumPy filter if measured need |
| HSMM (own) | No | Durations | Unproven | Medium | Medium | Cost; tuning | Repo | DEFERRED | P3 | Viterbi with minimum duration |
| FFmpeg | Not required | Render overlays | No; SRT plays in VLC | Medium | Low | Handling video locally only | LGPL/GPL* by build | DEFERRED | P3 | SRT |
| OpenCV | Starter docs only | Video decoding | No, not in tracking path | Medium | Medium | Heavy; video handling | Apache-2.0* | DEFERRED | P3 | None needed |
| Roboflow Supervision | No | Detection tooling | Phase 1: no | High | Medium | Models and datasets have separate licences; organisers must be able to access them | MIT* | DEFERRED | P3 | Provided tracking |
| Roboflow Sports | No | CV helpers; no PyPI package | Phase 1: no | High | High | Same; model and dataset terms not stated on its page | MIT | DEFERRED | P3 | Provided tracking |
| PyArrow | No | Parquet | No; arrays fit memory | Low | Low | Cache complexity | Apache-2.0* | REJECTED for phase 1 | n/a | `.npz` with hash key |
| Docker | No | Environment image | Lockfile is enough; adds platform issues | Medium | Medium | Time | Apache-2.0* (engine) | DEFERRED | P3 | uv lockfile |
| Kubernetes, GKE, cloud, databases, microservices | No | Nothing for this task | No | High | High | Time, data-handling risk | n/a | REJECTED | n/a | Local run |
| Deep sequence models | No | Learned decoder | No training labels at scale | High | High | Overfit, domain gap, reproducibility | n/a | DEFERRED | P3 | Viterbi |

**Core runtime additions:** none. **Development additions:** pytest, Ruff, uv.

Sources: [kloppy on PyPI](https://pypi.org/project/kloppy/), [FilterPy on PyPI](https://pypi.org/project/filterpy/),
[roboflow/sports](https://github.com/roboflow/sports).
