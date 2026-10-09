# Data boundaries

No datasets or generated images are included. `manifests/` holds versioned
metadata and split definitions. `raw/`, `external/`, `synthetic/` and
`ground_truth/` retain only README markers in Git. Never put labels or exact
generator transforms into inference manifests. Inspect redistribution rights
before adopting external samples; see [DATASETS](../docs/DATASETS.md).

Public schemas carry opaque image references; T03 maps them to trusted local
storage. Adapters must keep sequence order, dimensions, source coordinate
conventions and hashes. Do not infer track IDs from annotation array positions.
