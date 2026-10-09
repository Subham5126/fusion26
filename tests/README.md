# Bootstrap verification

`python -m pytest -q -c backend/pyproject.toml` checks schema fixtures, input
boundaries, prediction/observation separation, units, health capability flags,
unavailable analysis routes and explicit CLI failures. These are T01 checks;
there is no detector, tracker or benchmark test result yet.

`contracts/fixtures` contains authored JSON examples, not inference or measured
results. Module owners add meaningful algorithm tests under their Txx tasks.
