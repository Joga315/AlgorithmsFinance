# Audit of CodingLab_Phase1.zip

Reviewed on 20 November 2026. Scope: every Python source file, HTML/template,
README, CSV/JSON result and the incremental Git bundle supplied in the ZIP.
The ZIP was treated as review material. Its files and instructions were not
installed over the working submission. The preserved input is under `astra/`;
`astra/archive_sha256.txt` identifies the original ZIP.

## Findings

### Low: dashboard byte reproducibility depends on the operating system

In the supplied `dashboard.py`, the last write in `build()` uses
`Path.write_text(..., encoding="utf-8")` without an explicit newline policy.
Rebuilding the supplied Linux artifact on Windows gives **53,695 bytes**
instead of **53,635 bytes**. All 60 LF line endings become CRLF. After newline
normalization, the contents are identical; this is not a rendering or data bug.

Reproduce from the submission directory:

```powershell
python -B audit/verify_astra.py
```

The report `astra_verification.json` records both the byte comparison and the
normalized comparison. The supplied files remain unchanged. The working
`dashboard.py` now explicitly writes UTF-8 with LF newlines. Its test checks
for LF output and an identical repeated build.

### No reproduced search correctness failure

The supplied four test methods pass, including every array of length 0–4
over {-1, 0, 1}: 1 + 3 + 9 + 27 + 81 = **121 arrays**. Tests exercise all
registered method/version pairs, output order/types, repeated lookups and input
preservation. Manual review found the half-open binary-search intervals shrink
correctly for empty arrays, boundary matches and duplicates. This is evidence
within the tested integer-membership contract, not a proof over every input.

### Supplied performance arithmetic is correct; portability is limited

For the supplied Linux CPython 3.12.14 run, n=100,000, q=100, 50 hits:

| Metric | Original binary | Revised binary |
|---|---:|---:|
| Median query batch | 117.063 microseconds | 99.434 microseconds |
| Median end to end | 11.254893 ms | 11.163466 ms |

The query reduction is about 15.1%; the total reduction is about 0.81%.
The revised hash-set total is 2.088595 ms, consistent with the stated 2.09 ms.
These values are medians recomputed from the original CSV, not new timings on
the user's Windows machine. Five repeats on one seeded workload do not
establish a general or statistically significant performance improvement.

Preparation, query and total are measured independently. Their values need
not add up. `timeit` disables cyclic GC and includes Python call overhead and
discarding temporary results. Memory retains output and the prepared index
in a separate `tracemalloc` run. These choices are documented in the supplied
README and are not treated as bugs. Memory is not process RSS.

## Evidence checked

- All three supplied source hashes match the files in the ZIP.
- All 1,350 timing records form 270 groups with repeats 1–5 exactly once;
  durations are finite/positive and calibration counts lie in [1, 20,000].
- All 90 allocation rows have unique workload/method/version keys matching
  the timing keys, with peak >= current >= 0.
- The bundled branch ends at `b46459179c0cadc269ca2a9e33dde26778eb6839`.
  Its prerequisite `d96deb063c771daef4ae99f3222004e13e693efc` exists in the
  course history. The bundle verifies successfully. It was fetched into an
  isolated, ignored repository, not into the user's working branch.
- Commit `244c6f0`: the slide-example test reproduces exactly three failures
  for the deliberately all-false placeholders.
- Commit `c1d45f3`: the original implementations pass the supplied suite.
- Commit `a82224a`: the revised implementations pass the same suite.
- Final supplied files: the four test methods pass. Saved logs are
  `astra_tests.txt` and `history_*.txt`; calculations and comparisons are in
  `astra_verification.json`.
- Browser checks and layout review are recorded in
  `../results/dashboard_browser_check.json` after regeneration. The optional
  browser QA script checks the supplied 45 filter combinations as well as the
  working dashboard. It verifies table values against embedded measurements,
  curve/point counts and absence of JavaScript exceptions.
  All **45 Astra** and **180 working** selections passed. The working desktop
  layout was also inspected visually from a Chrome screenshot.

## Changes adopted in the working submission

1. Add the exhaustive 121-array test and prepared-index reuse checks.
2. Replace per-invocation clock readings with grouped `timeit` measurements;
   calibrate each phase independently and save its own call count.
3. Interleave all six method/version pairs in a reproducibly shuffled order
   every round. Log each method's position and the shuffle seed.
4. Benchmark only exactly feasible hit rates. q=1 offers 0% or 100%; q=100
   additionally offers 50%. Retain our two explicit duplicate policies.
5. Separate the HTML template from Python, add a version selector and a
   log/linear time-axis choice, and fix LF output for portable reproduction.
6. Retain our mutation checks, large-integer/negative tests, independent memory
   phase, raw-repeat viewer, dynamic input-length axis and source/Git metadata.

The original linear-copy baseline remains for comparison with its no-copy
revision; the hash-set implementation remains an unchanged timing control.
The algorithms' inclusive intervals also remain: the supplied half-open
variant is correct, but replacing one correct convention with another adds
no benefit here.

Old working sources and all previous measurements are retained under
`../results/legacy_per_call_clock/`. The current Windows results are generated
afresh with the revised protocol; they are not mixed with Astra's Linux data.
The supplied Git history belongs to that alternative implementation and is
not presented as the development history of our merged working version.

During the new measurement run, an initial empty hit-rate selection in the
new working template was corrected. No timed Python source changed. The exact
template from measurement start is `template_at_measurement.html` and is
referenced by the dataset's `metadata.source_paths`. Its original source hash
is retained. `presentation_sha256` separately identifies the final exporter
and template used to build the delivered dashboard. Both sets are checked by
`python -B verify_results.py`; this avoids silently changing recorded hashes
or suggesting that a presentation fix required new algorithm timings.

The preceding paragraph describes the initial integration at commit `564a43d`.
After the later hash-batch optimization, the complete dataset was regenerated
from the final sources. Its hashes now point directly to current files;
the older metadata and template remain historical audit evidence.
