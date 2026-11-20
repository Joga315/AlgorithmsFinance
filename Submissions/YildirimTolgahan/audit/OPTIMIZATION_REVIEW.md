# Hash-batch optimization and simpler dashboard

Requested after the first publication of PR #16. Baseline commit: `564a43d`.

## Implementation

- Preserve all three assignment methods and both versions. Linear/binary
  procedures remain implemented in Python; their search semantics are unchanged.
- Revised hash membership uses the bound built-in `set.__contains__` method
  through `map`, eliminating one Python wrapper call per query. The original
  version remains available for an interleaved same-input timing comparison.
- `HashIndex` explicitly owns a snapshot and handles multiple query batches.
  Reusing it avoids rebuilding a set for unchanged IDs. It does not maintain a
  hidden global cache or infer whether a mutable source has changed.
- The multi-batch experiment measures both scenarios end to end, including
  all index builds and lookups. Five batches reuse one fixed ID array; batches
  rotate the same queries so order is preserved and results remain comparable.

## Dashboard

The default view contains four controls, three methods, their timing bars,
the fastest optimized candidate for the selected case and a small table.
Original versions are added with a checkbox. Input-size curves, duplicate
settings, raw measurements and environment details are expandable.

The fastest label is computed from the selected saved timing component and
applies only to that measured case. "Mit Aufbau" includes preparation;
"Index schon vorhanden" excludes it and says so visibly. A distinct panel
reports the separately measured multi-batch experiment and its exact size.
No claim of a universally fastest algorithm is made.

## Validation

- 21 unit tests, including the existing exhaustive contract for all six
  versions and 121 small arrays. New tests cover repeated-index use, empty
  batches, independent output lists, source mutation, negative hash collisions
  and large integers. An export test covers embedding optional reuse results.
- Full same-input benchmark matrix regenerated: 30 workloads, 180 summary
  records and 900 raw repeats with independently timed phases.
- A separate five-round reuse experiment with source hashes and raw values.
- Saved-result verification checks the main dataset, all CSV values, median
  calculations, method order, exact source hashes, the reuse dataset and a
  byte-identical dashboard rebuild.
- Browser checks cover 180 working selections, table/bar values and fastest
  labels, all 45 preserved Astra selections, and a 390-pixel mobile viewport.
- Fresh-checkout tests and saved-result verification before push; the
  validation record is `optimization_validation.json`.

Measured gains and their workload are recorded in `../results/observations.md`.
Earlier results remain in Git history and the existing historical evidence
directories. Current results are new measurements of the changed sources;
old timings are not relabeled as optimized measurements.
