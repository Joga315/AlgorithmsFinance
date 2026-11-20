# Membership search in Python

Phase 1 of the Algorithms in Finance coding lab. Given an integer ID array and an ordered query batch, each method returns one Boolean per query and preserves both inputs. To explore the saved experiment, open **dashboard.html** in a browser. Keep the results folder beside it for the raw-data links.

## Run in VS Code

Open a terminal in this submission folder. On Windows, with Python 3 installed:

```powershell
py -3 -m unittest -v
py -3 benchmark.py
py -3 dashboard.py
Start-Process .\dashboard.html
```

On Linux or macOS use `python3` for the three Python commands, then open the HTML file. The implementation uses only the Python standard library. The shipped run used Python 3.12.14. The benchmark replaces the CSV and JSON files in results. The dashboard builder reads those files without running the benchmark. Expected test result: four test methods pass, including parameterized subtests for every registered method/version.

## Contract and revision

| Method | Preparation | Lookup per query | Extra prepared storage |
| --- | --- | --- | --- |
| Linear | Keep the input reference, O(1) | Scan until the first match, worst-case O(n) | O(1) |
| Binary | Sort a copy, worst-case O(n log n) | Halve a half-open interval, O(log(n+1)) comparisons for nonempty arrays | O(n) |
| Hash | Build a Python set, expected O(n) | Set membership, expected O(1) | O(u) for u distinct IDs |

Each batch additionally returns O(q) Booleans. Hash bounds assume ordinary hash behavior. Binary v1 recurses on index bounds, retaining O(log(n+1)) stack frames on nonempty inputs. Binary v2 updates the same bounds in a loop with O(1) search workspace. Linear and hash use the same functions in both versions and serve as timing controls.

For IDs [7, 11, 7], binary search prepares [7, 7, 11]. Query 11 exceeds the middle 7 and matches the right-hand 11. Query 9 visits 7 then 11 and exhausts its interval. Query 7 immediately matches. Every method therefore returns [True, False, True].

## Correctness evidence

The first commit (244c6f0) defined generator, tests and deliberately all-false placeholders. Running `python -m unittest test_search.MembershipTests.test_slide_example` there produced three failures. The original implementations (c1d45f3) passed the suite. The revision (a82224a) passed the same suite. The exhaustive test covers every array of length zero through four over {-1, 0, 1}, including duplicates, unsorted input and singleton arrays. Expected results use independent Python membership. Tests check Boolean types, order, repeated calls and input preservation.

AI assistance was used to write and run this submission. The implementation adopts a shared test contract and iterative binary search. It revises the earlier generator proposal of unique even IDs to sampling with replacement, exercising duplicates in the benchmark too. Sorting in place would violate the input contract, so both binary versions sort a copy.

## Reproduce the experiment

- Generate 1,000, 10,000 and 100,000 IDs using seed 42. Draw even IDs with replacement from n possible values. Sample hits from the array and misses from odd integers in the same numeric range. Shuffle the batch. IDs and queries may repeat.
- Compare exactly the same input lists across all six method/version pairs. For 100 queries use 0, 50 and 100 hits. A single query can only hit or miss, so use the two feasible cases. This yields 15 workloads.
- For each workload, shuffle method order reproducibly on each of five rounds. For each recorded phase, warm up once, then use timeit with an adaptive number of calls targeting 3 ms (maximum 20,000 calls). CSV seconds are elapsed time divided by calls. The figure shows the median of five recorded samples. Very short operations include Python call overhead.
- Preparation constructs a fresh index per timed call. Batch lookup uses one prepared index for that method and round. End-to-end calls prepare and query together, with fresh state on every call. It is measured independently, so the phase medians need not add up. Query times cover the complete batch. timeit disables cyclic garbage collection during timing. Discarding temporary return values is included.
- Allocation measurement runs separately with fresh tracemalloc tracing. Build inputs before tracing, then prepare and query once. Read current and peak traced bytes with the prepared index and output alive. The numbers cover Python-traced allocations during those operations and exclude prebuilt inputs. They do not quantify process RSS or the native call stack.
- Timings exclude data generation, correctness checks, tracing and rendering. Raw repeats and calibration counts are in results/timings.csv. results/memory.csv contains one allocation observation per workload/method/version. results/environment.json records machine details and SHA-256 digests of the measured Python sources.

## Result from the supplied run

For 100,000 IDs, 100 queries and 50 hits, the original binary query batch took 117.06 µs and the iterative version 99.43 µs (medians). End-to-end medians were 11.25 and 11.16 ms respectively. Sorting accounts for most of the cost at this workload. Revised hash membership took 2.09 ms end to end and linear scan 45.73 ms. These values describe this machine and seeded workload. Rebuild the dashboard after a new run to inspect its results.
