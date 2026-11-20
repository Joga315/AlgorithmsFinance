"""Separate timing and allocation runs; inputs and validation are never timed."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from time import perf_counter
import tracemalloc

from algorithms import METHODS
from data import make_workload

HERE = Path(__file__).resolve().parent


def timed_call(method, items, queries):
    start = perf_counter()
    prepared = method.prepare(items)
    prepared_at = perf_counter()
    answer = [method.contains(prepared, query) for query in queries]
    end = perf_counter()
    return answer, (prepared_at - start, end - prepared_at, end - start)


def measure(method, workload, repeats=5):
    if repeats < 5:
        raise ValueError("Use at least five repeats")
    items, queries = workload.items, workload.queries
    present = set(items)
    expected = [query in present for query in queries]
    before_items, before_queries = items.copy(), queries.copy()
    answer, warmup = timed_call(method, items, queries)
    if answer != expected:
        raise AssertionError("Incorrect warm-up answer")
    # Aggregate short calls to target about 2 ms per repeat; every call rebuilds
    # preparation. Clock readings bracket each call, excluding aggregation.
    calls = min(200, max(1, math.ceil(0.002 / max(warmup[2], 1e-9))))
    raw = []
    for repeat in range(repeats):
        elapsed = [0.0, 0.0, 0.0]
        for _ in range(calls):
            answer, times = timed_call(method, items, queries)
            # Validation is after the ending clock, outside each measurement.
            if answer != expected:
                raise AssertionError("Incorrect measured answer")
            elapsed = [a + b for a, b in zip(elapsed, times)]
        raw.append(dict(repeat=repeat + 1, calls=calls,
                        **{key: seconds * 1000 / calls for key, seconds in zip(
                            ("preparation_ms", "query_batch_ms", "total_ms"), elapsed)}))
    # Independent memory run: the input and expected answers exist before tracing.
    # The sorted copy / set and returned output stay alive through the reading.
    tracemalloc.start()
    try:
        prepared = method.prepare(items)
        output = [method.contains(prepared, query) for query in queries]
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if output != expected or items != before_items or queries != before_queries:
        raise AssertionError("Incorrect output or input mutation")
    return {
        "method": method.name, "version": method.version,
        "n": len(items), "q": len(queries), "seed": workload.seed,
        "requested_hit_rate": workload.requested_hit_rate,
        "actual_hit_rate": workload.actual_hit_rate,
        "duplicate_policy": workload.duplicate_policy,
        "distinct_ids": len(present),
        **{key: statistics.median(sample[key] for sample in raw)
           for key in ("preparation_ms", "query_batch_ms", "total_ms")},
        "current_traced_bytes": current, "peak_traced_bytes": peak,
        "raw_repeats": raw,
    }


def git_output(*args):
    result = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def source_hashes():
    return {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            for name in ("algorithms.py", "data.py", "benchmark.py", "test_lab.py", "dashboard.py")}


def run(output, sizes, counts, hit_rates, policies, repeats, seed):
    settings = dict(sizes=sizes, query_counts=counts, hit_rates=hit_rates,
                    duplicate_policies=policies, repeats=repeats, base_seed=seed)
    metadata = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "implementation": platform.python_implementation(),
        "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor(),
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_status_at_measurement": git_output("status", "--short"),
        "source_sha256": source_hashes(),
        "settings": settings,
        "units": {"time": "milliseconds per complete invocation (one query batch)", "memory": "bytes"},
        "protocol": "One warm-up per method/workload; fresh preparation every timed call; at least five repeats; medians of per-call batch durations. Short calls aggregated, up to 200 calls per repeat. Timing excludes input generation, validation, aggregation, memory tracing and rendering. Per-call clock overhead remains included. Method order rotated by workload.",
        "memory_protocol": "Separate fresh tracemalloc run for each method/version/workload. Input and queries allocated before tracing; prepared structures and returned output retained at reading. Reports current and peak traced Python bytes, not process RSS or mathematical auxiliary space. No native-memory completeness claim.",
    }
    rows = []
    cases = list(itertools.product(sizes, counts, hit_rates, policies))
    for index, (n, q, rate, policy) in enumerate(cases):
        work = make_workload(n, q, rate, seed + index, policy)
        offset = index % len(METHODS)
        for method in METHODS[offset:] + METHODS[:offset]:
            rows.append(measure(method, work, repeats))
        print(f"Workload {index + 1}/{len(cases)}: n={n}, q={q}, hits={work.actual_hit_rate:g}, {policy}", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / "measurements.json").write_text(json.dumps({"metadata": metadata, "rows": rows}, indent=2) + "\n", encoding="utf-8")
    columns = [key for key in rows[0] if key != "raw_repeats"]
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for row in rows)
    with (output / "raw_repeats.csv").open("w", newline="", encoding="utf-8") as stream:
        keys = ("method", "version", "n", "q", "requested_hit_rate", "actual_hit_rate", "duplicate_policy", "seed")
        repeat_keys = ("repeat", "calls", "preparation_ms", "query_batch_ms", "total_ms")
        writer = csv.DictWriter(stream, fieldnames=keys + repeat_keys)
        writer.writeheader()
        for row in rows:
            for sample in row["raw_repeats"]:
                writer.writerow({**{key: row[key] for key in keys}, **sample})
    print(f"Saved {len(rows)} rows and {len(rows) * repeats} raw repeats to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results")
    parser.add_argument("--sizes", type=int, nargs="+", default=[1000, 10000, 100000])
    parser.add_argument("--query-counts", type=int, nargs="+", default=[1, 100])
    parser.add_argument("--hit-rates", type=float, nargs="+", default=[0.0, 0.5, 1.0])
    parser.add_argument("--policies", nargs="+", choices=["unique", "duplicates"], default=["unique", "duplicates"])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    if args.repeats < 5 or min(args.sizes) < 1 or min(args.query_counts) < 1 or any(not 0 <= rate <= 1 for rate in args.hit_rates):
        parser.error("Use positive sizes/counts, at least five repeats, and hit rates in [0,1]")
    run(args.output, args.sizes, args.query_counts, args.hit_rates, args.policies, args.repeats, args.seed)


if __name__ == "__main__":
    main()
