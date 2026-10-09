# Decision log

Initial decisions are proposed defaults from this planning task. The team adopts or modifies them at kickoff.

| ID | Decision | Reason | Revisit trigger |
|---|---|---|---|
| D01 | Synthetic-first P0 | Explicit PS permission and known truth | Full core working and real data available |
| D02 | CPU classical detector first | Avoid training dependency | Demonstrated detector bottleneck + usable compute |
| D03 | React/FastAPI, Streamlit fallback | Clear demo and module separation | Team smaller or no live integration at hour 12 |
| D04 | Image-plane trajectory | Satisfies rough-path scope with declared limits | Reliable astrometric metadata available |
| D05 | Shared schema v0.1.0 | Reduce parallel integration failures | Reviewed migration with all consumers updated |
| D06 | No identity claim for debris | Images/short tracks insufficient for verified identity | Catalog correlation and independent evidence |
| D07 | spotGEO is a separate profile | Different acquisition/morphology | Adapter proven on inspected samples |
| D08 | External data ignored by Git | Size and provenance/rights | Licensed tiny example is deliberately adopted |
| D09 | Local/offline demo required | Event network uncertainty | Still retain local demo if later deployed |

## Change entry template

```markdown
## Dxx — title
Date / hackathon hour:
Owner:
Context and observed evidence:
Decision:
Files/contracts affected:
Alternatives considered briefly:
Validation required:
Revisit trigger:
```

Integration writes shared decisions. Workers propose decisions in handoffs to prevent concurrent edits.
