# Risk register and fallbacks

| Risk | Early sign | Owner | Response |
|---|---|---|---|
| Real-data domain mismatch | YOLO/body detector misses faint sources | B | Use telescope-specific proposals; keep real validation separate |
| Registration failure | Stars leave many residuals; transform drift | B | Verify transform on known synthetic cases; restrict supported mode |
| Target erased by background model | Slow source vanishes after preprocessing | B | Direct compact-source path and profile-specific logic |
| False hot-pixel tracks | Static artifacts become confirmed | B/C | Sensor/morphology evidence; negative benchmark; ambiguity flag |
| Association swap | IDs switch at crossings | C | Gate and appearance cues; report ambiguity and ID switches |
| Label leakage | Detector reads annotation directory | A/C | Separate truth path; enforce interfaces; audit imports/data access |
| “Accuracy” based on prediction points | Gap fills increase detection TP | C | Distinct point types; evaluator scores observations separately |
| Dataset download delay | Archive unavailable by hour 6 | B | Stop blocking; seeded synthetic route |
| GPU or training stall | No useful trained detector by hour 8 | B | Drop training; CPU baseline |
| UI/API divergence | Inconsistent field names by hour 6 | A/D | Contract fixtures and owner-controlled schema changes |
| Full stack not integrated | UI still mocked at hour 12 | A/D | CLI + simple viewer/Streamlit fallback |
| Unverified rights | License absent from actual archive | A/B | Do not redistribute external assets; provide links and synthetic samples |
| Misleading physical claims | px/frame labeled km/s | All | Enforce units and candidate wording |
| Last-minute dependency failure | Works only on one machine | A | Clean install at hour 18; preserve working snapshot |
| Submission mismatch | Unknown upload format/deadline | A | Confirm organizer instructions early |

## Risk posture

Prefer a narrow complete pipeline with honest evaluation over many unfinished features. A failed real-data attempt can be discussed as a limitation; it should not become fabricated validation. Drop scope at checkpoints, not correctness.
