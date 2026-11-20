"""Timing benchmark. Run with:  python benchmark.py   (add --quick for a fast trial)

What is timed (elapsed seconds, time.perf_counter):
    prepare_s : building the prepared structure (sorted copy / hash set; 0 work for linear)
    query_s   : the complete batch of q queries on that prepared structure
    total_s   : prepare_s + query_s  (both measured in the same repeat)
All values are PER COMPLETE BATCH, not per query.

Rules followed (slides 59-60):
    * identical inputs for every method and version (same seed per setting)
    * data generation, tests, printing and plotting are outside the timed region
    * one untimed warm-up, then 5 timed repeats; the median is reported
    * a FRESH prepared structure is built in every repeat
    * very short operations are timed `inner` times in a row and divided by `inner`
    * raw repeat values are saved, with environment metadata
Timing is run separately from memory tracing (see memory.py).
"""
import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from data import make_ids, make_queries
from membership import METHODS

SEED = 20261120
REPEATS = 5
MIN_BLOCK_S = 0.002  # a timed block shorter than this is repeated `inner` times
DUPLICATES = "none"


def inner_count(fn):
    """How many back-to-back calls are needed so one timed block lasts >= MIN_BLOCK_S."""
    t0 = time.perf_counter()
    fn()
    once = time.perf_counter() - t0
    if once >= MIN_BLOCK_S:
        return 1
    return min(10_000, max(1, int(MIN_BLOCK_S / max(once, 1e-9)) + 1))


def time_block(fn, inner):
    t0 = time.perf_counter()
    for _ in range(inner):
        fn()
    return (time.perf_counter() - t0) / inner


def measure(method, ids, queries):
    prepare, query, _ = METHODS[method]
    # warm-up (untimed), also used to choose the inner counts
    prepared = prepare(ids)
    query(prepared, queries)
    inner_p = inner_count(lambda: prepare(ids))
    prepared = prepare(ids)
    inner_q = inner_count(lambda: query(prepared, queries))

    rows = []
    for rep in range(REPEATS):
        # preparation: every call builds a fresh structure
        prep_s = time_block(lambda: prepare(ids), inner_p)
        prepared = prepare(ids)  # fresh state for this repeat's query batch
        query_s = time_block(lambda: query(prepared, queries), inner_q)
        rows.append((rep, prep_s, query_s, prep_s + query_s, inner_p, inner_q))
    return rows


def git_commit():
    """Code version. Inside Docker there is no .git folder, so pass it in with
    -e CODE_COMMIT=$(git rev-parse HEAD) (see README)."""
    env = os.environ.get("CODE_COMMIT")
    if env:
        return env
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             cwd=Path(__file__).parent)
        return out.stdout.strip() or "not a git checkout"
    except OSError:
        return "git not available"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small grid for a fast trial run")
    args = ap.parse_args()

    sizes = [1_000, 10_000] if args.quick else [1_000, 10_000, 100_000]
    query_counts = [1, 100]
    hit_rates = [1.0, 0.0, 0.5]  # all-present, all-absent, mixed

    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    raw_rows, summary_rows = [], []

    for n in sizes:
        ids = make_ids(n, SEED, DUPLICATES)
        for q in query_counts:
            for hit in hit_rates:
                queries = make_queries(ids, q, hit, SEED)
                ids_before = list(ids)
                for method, (_, _, version) in METHODS.items():
                    reps = measure(method, ids, queries)
                    assert ids == ids_before, f"{method} modified the input"
                    for rep, p, qs, tot, ip, iq in reps:
                        raw_rows.append([method, version, n, q, hit, rep, p, qs, tot, ip, iq])
                    summary_rows.append([
                        method, version, n, q, hit,
                        statistics.median(r[1] for r in reps),
                        statistics.median(r[2] for r in reps),
                        statistics.median(r[3] for r in reps),
                    ])
                    print(f"n={n:>6} q={q:>3} hit={hit:.1f} {method:<9} "
                          f"total median {summary_rows[-1][-1]*1e3:9.3f} ms")

    head = ["method", "version", "n", "q", "hit_rate"]
    with open(out / "timing_raw.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head + ["repeat", "prepare_s", "query_s", "total_s", "inner_prepare", "inner_query"])
        w.writerows(raw_rows)
    with open(out / "timing_summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(head + ["prepare_median_s", "query_median_s", "total_median_s"])
        w.writerows(summary_rows)

    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "code_commit": git_commit(),
        "seed": SEED,
        "duplicates_policy": DUPLICATES,
        "id_generator": "distinct even integers from range(0, 20n+20), random order",
        "absent_queries": "odd integers (guaranteed absent)",
        "sizes": sizes, "query_counts": query_counts, "hit_rates": hit_rates,
        "repeats": REPEATS, "warm_up": "one untimed run per setting",
        "min_block_seconds": MIN_BLOCK_S,
        "units": "seconds per complete batch (prepare, query batch, total)",
        "clock": "time.perf_counter",
    }
    (out / "environment.json").write_text(json.dumps(meta, indent=2))
    print(f"saved {out/'timing_raw.csv'}, {out/'timing_summary.csv'}, {out/'environment.json'}")


if __name__ == "__main__":
    main()
