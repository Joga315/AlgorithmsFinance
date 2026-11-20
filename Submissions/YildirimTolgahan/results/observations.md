# Optimized search measurements

Fresh CPython 3.13.12 Windows run. n=100,000, q=100, 50 hits, unique IDs.

| Method / version | Preparation (ms) | Query batch (microseconds) | Total (ms) | Peak (KiB) |
|---|---:|---:|---:|---:|
| linear / original | 1.116467 | 388031.500 | 399.142800 | 782.24 |
| linear / revised | 0.000196 | 445899.500 | 387.614600 | 0.94 |
| binary / original | 31.635600 | 598.600 | 30.639400 | 1171.79 |
| binary / revised | 36.769100 | 478.567 | 37.571600 | 1171.79 |
| hash_set / original | 12.447600 | 19.656 | 16.603700 | 6144.26 |
| hash_set / revised | 14.265700 | 7.455 | 13.882300 | 6144.26 |

In this case, optimized hash lookup is 2.64x as fast as the original query wrapper. Total times also include construction and vary independently.

## Reusing the index

Separate experiment: 5 batches, 100,000 unchanged IDs and 100 queries per batch.

- Build per batch: 124.098400 ms.
- Build once: 26.058600 ms.
- Measured ratio: 4.76x.

Both totals include construction and every query. Rebuild the snapshot when IDs change.

## Interpretation

These are descriptive medians from five randomized rounds. They do not establish a universally fastest method or statistical significance. Preparation, query and total are timed independently and need not add up. Compare the same workload and cost scope; the dashboard selects the fastest measured revised method for the chosen case.

Full raw data, environment and code hashes are in measurements.json and reuse.json. Original versions remain visible in the dashboard. Earlier datasets remain in Git history and the existing historical evidence folders.
