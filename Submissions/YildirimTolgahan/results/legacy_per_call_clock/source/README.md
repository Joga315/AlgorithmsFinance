# Search methods — Tolgahan Yildirim

Phase 1 of the *Algorithms in Finance* coding lab. All files are confined to
`Submissions/YildirimTolgahan/`. No third-party packages or Docker are required.

## Run from a fresh checkout

Reference environment: CPython **3.13.12**, Windows x64. The code uses Python
3.10+ syntax and only its standard library. `requirements.txt` records that
there are no external dependencies to install or pin.

From the repository root in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
cd Submissions\YildirimTolgahan
python -B -m unittest discover -v
python -B benchmark.py
python -B dashboard.py
Start-Process .\results\dashboard.html
```

If the project environment already exists, start with activation. Check
`python --version` before running. On macOS/Linux, use `python3 -m venv .venv`,
`source .venv/bin/activate`, and `cd Submissions/YildirimTolgahan`; open the HTML
with any modern browser. No web server, internet connection, dashboard port or
API key is needed to run this project.

Expected test result: **13 tests, OK**, including shared subtests for every
method/version. The course's `Class1-2` demonstration is a separate project.

For a quick end-to-end run without replacing the submitted measurements:

```powershell
python -B benchmark.py --sizes 100 1000 --query-counts 1 10 --output results/smoke
python -B dashboard.py --results results/smoke/measurements.json --output results/smoke/dashboard.html
```

## Specification and tests first

An integer array and ordered query batch produce a list of actual Python
Booleans in query order. Neither input is changed. Tests cover empty arrays
and queries, singleton inputs, duplicates, unsorted inputs, first/last values,
absent values, repeated calls, negative/large integers and generated examples.
The slide example `[7, 11, 7]`, `[11, 9, 7]` gives `[True, False, True]`.

Tests and the synthetic generator were written before implementation.
`results/test_before.txt` records the run against `NotImplementedError`
placeholders. The same search tests remain after implementation; measurement
and HTML-export tests were added afterwards. Passing these tests is evidence,
not a proof of correctness.

Small manual trace: sorted copy `[7, 7, 11]`, query `9`: check index 1 (`7`),
then index 2 (`11`), then the interval is empty → `False`. Query `11` reaches
index 2 → `True`. The caller's original `[7, 11, 7]` remains unchanged.

## Methods and revision

| Method | Original | Revised |
|---|---|---|
| Linear | Copy the input once, then scan for every query | Scan the existing input without a redundant copy |
| Binary | Sort a copy, then recurse over index intervals | Sort a copy, then search iteratively |
| Hash set | Construct a set, then use membership | Same implementation, retained as a control |

Linear and both binary search procedures are implemented here. Library sorting
and sets are explicitly permitted. No `bisect`, library search procedure or
array-membership shortcut is used for the two search implementations.

For linear search, the processed prefix contains no match; returning early
finds an equal item, and exhausting the array rules one out. For binary search,
any possible match stays in the inclusive interval `[left, right]`; each
failed comparison excludes the middle and an impossible half. The interval
strictly shrinks, including on duplicate values. Set membership has the same
integer equality semantics. No method mutates its input.

The linear revision avoids O(n) preparation time and allocation. Both binary
versions use O(log n) comparisons per query, with O(log n) recursive stack
space originally and O(1) search stack space after revision. Both still pay
for sorting a copy; Python's sorting also has workspace costs. Hash-set
construction uses O(n) expected time and O(u) storage for u distinct IDs;
membership is expected O(1), with collision-dependent worst cases. Every
method additionally builds an O(q) output list. Total costs must include
preparation. These bounds do not predict exact timings or guarantee that a
revision wins every measured case.

## Fixed workloads and measurement definitions

The default run uses n ∈ {1,000; 10,000; 100,000}, q ∈ {1; 100}, requested hit
rates {0%; 50%; 100%}, and two duplicate policies: **36 workloads**, each run
with all six method/version combinations (**216 summary rows**, **1,080 raw
repeats**). Input/query order is identical across methods and versions within
a workload. Method execution order rotates between workloads.

`data.py` uses its own seeded `random.Random`. Unique inputs are shuffled even
IDs. Duplicate inputs draw n even IDs with replacement from max(1, n//4)
possible values. Absent queries are odd. Present queries sample existing
items with replacement. Query order is shuffled. The hit count rounds
`q * requested_hit_rate` to the nearest integer, with halves rounded up.
**A single query cannot have a 50% hit rate**: that setting produces one hit.
Both requested and achieved rates, seeds, duplicate policy and distinct-ID
counts are saved and shown in the dashboard.

- Timing uses `time.perf_counter()`, one warm-up and five repeats. Short calls
  are aggregated to target approximately 2 ms per repeat, capped at 200 calls.
  Every timed invocation creates fresh preparation state. Each raw repeat
  reports average milliseconds per complete invocation, not per query.
- Clock readings separate preparation (copy/sort/set construction), complete
  query batch, and their combined time. Raw total equals the sum of the raw
  components; the median total need not equal the sum of component medians.
  Clock overhead remains included, so sub-microsecond results need caution.
- Generation, expected answers, validation, aggregation, memory tracing and
  HTML rendering are outside the timed intervals. Output construction is
  included. No profiler runs during timings.
- Memory uses a **separate fresh `tracemalloc` run** per row. Input, queries
  and expected answers exist before tracing. Prepared structures and the
  output remain alive through the current/peak reading. Values are traced
  Python bytes; the dashboard converts these to KiB. They exclude pre-existing
  inputs and do not claim to measure all native memory, process RSS or
  mathematical auxiliary space. A single memory reading is not a distribution.
- Metadata includes Python/OS/CPU details, UTC time, settings, Git HEAD and
  working-tree status. SHA-256 hashes identify the actual source files even
  when measurements precede a commit. Timings vary with host load and runtime.

## Files and dashboard

| File | Purpose |
|---|---|
| `algorithms.py` | Original/revised implementations and common batch contract |
| `data.py` | Seeded synthetic data, separate from measurement |
| `test_lab.py` | Contract, generator, measurement and export tests |
| `benchmark.py` | Timing, independent memory measurement, JSON/CSV export |
| `dashboard.py` | Generate an interactive standalone HTML file from saved JSON |
| `results/measurements.json` | Full raw repeats, medians and environment |
| `results/summary.csv`, `results/raw_repeats.csv` | Tables for independent analysis |
| `results/dashboard.html` | Open locally; filter by q, hit rate, duplicate policy and time component |
| `results/test_before.txt`, `results/test_after.txt` | Recorded validation runs |

The dashboard plots one curve per method/version and includes timing, current
and peak memory tables, raw repeats and environment details. It embeds saved
JSON; filtering does not rerun measurements. Rerun `dashboard.py` after updating
measurements. Keep HTML, JSON and CSV together for the download links.

## Observations from the saved run

For n=100,000, q=100, all queries absent and unique input IDs:

| Method / version | Median total (ms) | Peak traced (KiB) |
|---|---:|---:|
| Linear / original | 957.402 | 782.24 |
| Linear / revised | 1,103.834 | 0.94 |
| Binary / original | 42.875 | 1,171.79 |
| Binary / revised | 46.868 | 1,171.79 |
| Hash set / original | 16.908 | 6,144.26 |
| Hash set / revised | 18.297 | 6,144.26 |

Removing the linear copy reduces preparation from 0.9434 ms to 0.0019 ms and
substantially reduces traced memory in this case. It does **not** produce a
lower total time in this run: scanning dominates. Iteration also does not win
this particular binary-search measurement, although it eliminates recursive
stack growth. The unchanged hash-set control has different timing medians
between labels, illustrating run-to-run variability. These data support a
memory improvement, not a universal runtime improvement. Other workloads and
all repeats remain available for comparison in the dashboard and CSV files.

Validation: all 13 tests pass under CPython 3.13.12. The exported JSON/CSV row
counts, raw-component sums, medians, finite nonnegative durations, memory
ordering and source hashes were checked. Chrome rendered all six curves and
passed all 36 dashboard filter combinations without JavaScript exceptions;
the browser check is recorded in `results/dashboard_browser_check.json`.

## AI assistance and audit handoff

Codex generated the implementation, tests, measurement/export code and this
documentation with AI assistance. Accepted suggestions: assertions/unittest
instead of an extra test dependency; an offline dashboard; removing the
linear copy and replacing recursion with iteration. Corrected design choices:
the recursive helper uses explicit arguments to avoid a self-referential
closure, and the dashboard exposes achieved hit rates for q=1. Rejected
assumptions: preparation is free, a revision always wins, traced memory is
process memory, or passing tests proves correctness. This documents the AI
contribution; the submitted work should retain this disclosure.

After review, commit these files and record the resulting commit SHA for the
peer audit. Do not invent a submission SHA before committing. No Pull Request
is opened automatically. Phase 2 requires another student's chosen commit;
this directory currently implements Phase 1 only. A future audit must preserve
the target version and distinguish reproduced bugs from suspected weaknesses.
