# Algorithms in Finance — Joga Singh

## Goal
Compare linear search, binary search on a sorted copy,
and membership using a Python set.

## Phase 1 specification

Each method accepts an integer ID list and an ordered integer query list and
returns a list of actual Python `bool` values, one per query in the same
order. Inputs remain unchanged. `linear_search` scans the IDs,
`binary_search` searches a sorted copy, and `hash_membership` constructs one
set per call. The original recursive and revised iterative binary-search
versions implement this same contract.

The specification suite checks explicit expected answers, boundary and
negative values, duplicates, ordering, repeated calls, input preservation, and
the result type. Each case runs against all three methods in both versions.
The saved preimplementation baseline has 39 intentional
`NotImplementedError` failures; see `results/tests_before_implementation.txt`.
The original implementation's 39 passing cases are in
`results/tests_initial_implementation.txt`; the revised suite's 78 cases are
in `results/tests_after_revision.txt`.

## Project structure

```text
Submissions/SinghJoga/
  algorithms/search.py             revised methods
  algorithms/search_v1.py          preserved recursive baseline
  data/generate.py                 reproducible synthetic cases
  tests/test_search.py             shared specification tests
  benchmarks/run_benchmarks.py     timing and memory runner
  results/                         saved results and verification evidence
  dashboard/app.py                 saved-results Streamlit dashboard
  docs/walkthrough.md              AI-labeled worked traces
  requirements.txt                 pinned Python dependencies
```

## PowerShell setup and commands

From the repository root, create and activate the submission virtual
environment once, then install the pinned dependencies. Skip the `venv`
creation command if `.venv` already exists:

```powershell
Set-Location '.\Submissions\SinghJoga'
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

After activation, these commands run the generator, tests, benchmark stages,
and dashboard:

```powershell
python data\generate.py --n 10 --q 4 --hit-rate 0.5 --seed 42
python -m pytest -q
python -m benchmarks.run_benchmarks --smoke
python -m benchmarks.run_benchmarks
python -m streamlit run dashboard\app.py
```

The test command currently reports **78 passed**. The smoke and full
benchmark commands save to `results/benchmark_smoke.json` and
`results/benchmark_results.json`. The dashboard uses Streamlit's default
port **8501**.

## Synthetic data

Generate and print a reproducible case from this folder:

```powershell
python data\generate.py --n 10 --q 4 --hit-rate 0.5 --seed 42
```

`--n` sets the number of IDs, `--q` the number of ordered queries,
`--hit-rate` the requested fraction of present queries, and `--seed` the
random seed. The requested hit count is `int(q * hit_rate + 0.5)`. IDs are
non-negative integers sampled with replacement from `[0, 10*n]`, so
duplicates are allowed. Present queries are sampled from the IDs; absent
queries are negative integers sampled with replacement from `[-q, -1]`, and
query order is shuffled. Expected answers are calculated independently from
the generated IDs. The JSON metadata keeps both requested and actual hit
rates; with `q=1`, a 50% actual rate is impossible. The optional
`--output PATH` saves the same JSON and creates missing parent directories.

Negative absent queries are a controlled workload choice: their ordering and
values can influence binary-search performance.

## Specification tests

From this folder, run:

```powershell
python -m pytest -q
```

Implemented methods in `algorithms/search.py`:

- `linear_search` scans the ID list for each query.
- `binary_search` iteratively searches a sorted copy using left/right index
  bounds. It replaces the recursive approach in `algorithms/search_v1.py` to
  remove recursive calls and recursive stack usage.
- `hash_membership` builds a set once and checks each query.

Both versions still allocate a sorted copy for binary search and a new output
list for each method. Measurements are recorded below; no speedup claim is
made.

The same 39 specification cases run against all three methods in both
versions: **78 passed** with `python -m pytest -q`. The exact command and
output are recorded in `results/tests_after_revision.txt`. The unchanged
initial implementation is preserved in `algorithms/search_v1.py`.

AI-use disclosure: AI assistance generated or revised the search
implementations, synthetic-data generator, specification tests, benchmark
runner, dashboard, and supporting documentation. The worked traces are
AI-generated review aids, not evidence of personal manual work.

Review the worked method trace in `docs/walkthrough.md`.

## Measurement stage

Run the smoke check first, then the full matrix, from this folder using the
existing virtual environment:

```powershell
python -m benchmarks.run_benchmarks --smoke
python -m benchmarks.run_benchmarks
```

The smoke result is `results/benchmark_smoke.json`; the full result is
`results/benchmark_results.json`. The full matrix uses `n` values `1000`,
`10000`, and `100000`, `q` values `1` and `100`, and requested hit rates
`0`, `0.5`, and `1`. It records the actual generator seed for each workload:
full-matrix seeds begin at `20261120` and increment in `n`, `q`, hit-rate loop
order. The smoke seed is `20261119`. Each generated input is shared by all
three methods in both versions. All public and adapter answers are validated
outside timing against the generator's expected answers. Generator version,
requested and achieved hit rates, duplicate policy, Python/platform details,
Git HEAD and dirty status, and relevant source SHA-256 hashes are in the JSON.

With `q=1`, a requested `0.5` hit rate cannot be genuinely mixed. The recorded
workloads show the achieved `1.0` rate and mark `genuinely_mixed` false.

Timing uses `time.perf_counter()`. Each operation is warmed up once; batch
sizes start at one call and double until the batch reaches `0.005` seconds or
the `2048`-call cap. The selected batch counts and calibration outcomes are
recorded. Five repeat values are retained. Binary preparation includes
`sorted(ids)` and hash preparation includes `set(ids)`; linear preparation is
a no-copy adapter pass-through of the original IDs. Adapter query time
includes allocating the result list and is for one complete ordered batch of
`q` queries, not per query. Query-only adapter calls reuse a prepared state
created outside that component timer. For each repeat, preparation time per
call and query time per complete batch are summed, then the median of those
five sums is reported.

Component timings measure the benchmark adapters, not direct public-method
calls. The separately reported public end-to-end times call the actual method
and include its own preparation, complete query batch, and output allocation.
Input generation, correctness checking, warm-up, calibration, printing,
file output, and memory tracing are excluded from timing.

Memory is measured separately for every version/method/workload with a fresh
`tracemalloc` session around the actual public method. Inputs are generated
before tracing, so input allocations are excluded; preparation and output
allocations are included. The returned output stays alive while current and
peak bytes are read. Temporary preparation structures may be freed before
the current reading, while peak captures their traced high-water mark.
`tracemalloc` reports traced Python allocations, not total process memory or
theoretical auxiliary space.

The saved full matrix covers 18 workloads, 108 timing records, and 108
separate memory records. For binary search, compare the 18 matched
workload-level medians for the original and revised versions:

- The complete-query-batch adapter median was lower for the iterative version
  in all 18 pairs; the median paired revised/original ratio was `0.802`
  (19.8% lower).
- The combined preparation-plus-query component median was lower in 14 of 18
  pairs; the median paired ratio was `0.978` (2.2% lower).
- Direct public-method end-to-end medians were lower in 15 of 18 pairs; the
  median paired ratio was `0.958` (4.2% lower). At `n=100000`, the paired
  results split evenly, with a median relative difference of about 0.14%
  higher for the iterative version.

These are observed differences in five-repeat medians on one machine, not
proof of a general speedup. In particular, the direct end-to-end difference
at the largest input size is effectively inconclusive; the query-adapter
measurement excludes preparation and is not a public-method timing.

For binary-search memory, the median current/peak traced bytes across the six
workloads at each `n` were:

| `n` | Original current / peak | Iterative current / peak |
|---:|---:|---:|
| 1,000 | 9,613 / 12,168 | 808 / 12,088 |
| 10,000 | 81,901 / 120,192 | 824 / 120,112 |
| 100,000 | 801,997 / 1,200,048 | 824 / 1,199,968 |

The large current-memory difference is consistent with the recursive nested
helper retaining its sorted copy through a self-referential closure until
cyclic garbage collection, while the iterative method releases its local
sorted copy on return. Peak medians differ by only 80 bytes at each input
size. These are traced Python allocation measurements; current and peak
values do not represent total process memory or theoretical auxiliary space.

The recorded environment was Python 3.14.7 on Windows 11 (AMD64; Intel64
Family 6 Model 142 Stepping 12). The benchmark JSON records five repeats,
batch counts, calibration details, seeds, achieved hit rates, and source
hashes. Recompute the full matrix only when the measured source files no
longer match those hashes or the workload needs to change.

All four saved benchmark SHA-256 values for `algorithms/search.py`,
`algorithms/search_v1.py`, `data/generate.py`, and
`benchmarks/run_benchmarks.py` match the current submission files. The saved
run records Git HEAD
`a80e2d2409903378e6a10ae82efa8f51819897ea` and
`dirty_working_tree: true`; the measurements were made from a dirty working
tree and are not represented as a clean-commit run. The matching hashes mean
the saved results correspond to the submitted algorithm, generator, and
benchmark code, so no rerun was needed.

Docker was not used.

## Runtime dashboard

From this submission folder, install the pinned dependencies and launch the
Streamlit dashboard:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run dashboard\app.py
```

Streamlit uses port **8501** by default. The dashboard reads the saved
`results/benchmark_results.json` relative to its own file and only displays
recorded results; changing filters never reruns benchmarks. It shows achieved
hit rates, component and public-method timing charts, memory results, raw
repeats and batching counts, and environment metadata. If the results file is
missing, the dashboard displays the benchmark command needed to create it.
The verification record is in `results/dashboard_verification.txt`.