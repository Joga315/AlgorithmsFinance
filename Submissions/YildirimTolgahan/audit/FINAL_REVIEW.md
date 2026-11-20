# Final submission review

Reviewed on 20 November 2026, before publishing the Phase 1 submission.
This is the historical initial-publication review (commits `94ec0bf` and
`564a43d`). For the later performance and dashboard changes, see
`OPTIMIZATION_REVIEW.md` and `optimization_validation.json`.

## Findings corrected

1. **Checkout reproducibility:** the host has `core.autocrlf=true`. Without a
   submission-local override, Git can change the bytes of measured source and
   archived evidence on checkout, invalidating their SHA-256 digests. The local
   `.gitattributes` now disables newline conversion for this submission.
2. **Verification under optimized Python:** both verification scripts used
   assertions. Python `-O`/`-OO` removes assertions, potentially allowing an
   unchecked PASS report. Both scripts now reject optimized execution.
3. **Submission instructions:** the README now identifies the PR head as the
   peer-review version and distinguishes the alternative-version comparison
   from the separate Phase 2 peer audit.

No remaining correctness blocker was identified in the integer-membership
contract. Linear and both binary searches were inspected and exercised with
empty inputs, duplicates, boundaries, negative/large integers, unchanged
inputs, repeated queries and all 121 arrays of length 0–4 over {-1,0,1}.

## Validation

- 17 unit tests, including six method/version combinations and exhaustive cases.
- Saved-data checks for 180 summary rows and 900 repeats (2,700 phase samples),
  including CSV agreement, medians, method order, source hashes and exact HTML
  reconstruction. Original archived-source hashes are preserved separately.
- Repeated audit of the supplied ZIP, historical failing/passing tests and
  source/result consistency.
- Browser verification: 45 alternative-version views and 180 working views,
  with table/data agreement and no JavaScript exceptions.
- Tests and saved-data verification from a fresh local clone with
  `core.autocrlf=true`; a small benchmark/export/verification run also checks
  the complete execution path without overwriting submitted measurements.
- Optimized-Python rejection, staged whitespace checks, file-scope review and
  common credential/private-key pattern scan before publishing.

Validation output is saved in `final_validation.json`. Benchmark timings are
descriptive measurements of the recorded machine and workload. They do not
establish a universal speedup; the unchanged hash-set control also varies.
The timed algorithms and benchmark implementation were not changed during
this final review, so existing timings remain associated with their recorded
source hashes. No new full timing run is claimed.
