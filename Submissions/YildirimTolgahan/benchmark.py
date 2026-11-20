"""Grouped timeit measurements, interleaved rounds and separate memory runs."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
from timeit import Timer
import tracemalloc

from algorithms import METHODS
from data import make_workload

HERE = Path(__file__).resolve().parent
TIME_KEYS = ("preparation_ms", "query_batch_ms", "total_ms")
CALL_KEYS = ("preparation_calls", "query_batch_calls", "total_calls")


def timed_phase(operation):
    """Warm up/calibrate outside the sample, then time a group of fresh calls."""
    timer = Timer(operation)
    elapsed = timer.timeit(1)
    calls = min(20000, max(1, math.ceil(0.003 / max(elapsed, 1e-9))))
    return timer.timeit(calls) * 1000 / calls, calls


def memory_reading(method, items, queries, expected):
    tracemalloc.start()
    try:
        prepared = method.prepare(items)
        output = method.lookup(prepared, queries)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    if output != expected:
        raise AssertionError("Incorrect memory-run answer")
    return current, peak


def measure_methods(methods, workload, repeats=5, order_seed=2026):
    """One shared workload, independently shuffled method order every round."""
    if repeats < 5:
        raise ValueError("Use at least five repeats")
    if tracemalloc.is_tracing():
        raise RuntimeError("Stop external memory tracing before timing")
    items, queries = workload.items, workload.queries
    present = set(items)
    expected = [query in present for query in queries]
    before_items, before_queries = items.copy(), queries.copy()
    methods = tuple(methods)
    samples = {(m.name, m.version): [] for m in methods}
    if len(samples) != len(methods):
        raise ValueError("Method/version pairs must be unique")

    def validate_inputs():
        if items != before_items or queries != before_queries:
            raise AssertionError("Input mutation")

    rng = random.Random(order_seed)
    for repeat in range(1, repeats + 1):
        order = list(methods)
        rng.shuffle(order)
        for position, method in enumerate(order, 1):
            prepared = method.prepare(items)
            if method.lookup(prepared, queries) != expected:
                raise AssertionError("Incorrect preflight answer")
            validate_inputs()
            operations = (
                lambda: method.prepare(items),
                lambda: method.lookup(prepared, queries),
                lambda: method.answer(items, queries),
            )
            sample = {"repeat": repeat, "method_position": position}
            for time_key, call_key, operation in zip(TIME_KEYS, CALL_KEYS, operations):
                sample[time_key], sample[call_key] = timed_phase(operation)
                validate_inputs()
            if method.answer(items, queries) != expected:
                raise AssertionError("Incorrect post-timing answer")
            validate_inputs()
            samples[method.name, method.version].append(sample)

    # All timing rounds finish before starting any memory tracing.
    rows = []
    for method in methods:
        current, peak = memory_reading(method, items, queries, expected)
        validate_inputs()
        raw = samples[method.name, method.version]
        rows.append({
            "method": method.name, "version": method.version,
            "n": len(items), "q": len(queries), "seed": workload.seed,
            "order_seed": order_seed,
            "requested_hit_rate": workload.requested_hit_rate,
            "actual_hit_rate": workload.actual_hit_rate,
            "duplicate_policy": workload.duplicate_policy,
            "distinct_ids": len(present),
            **{key: statistics.median(sample[key] for sample in raw) for key in TIME_KEYS},
            "current_traced_bytes": current, "peak_traced_bytes": peak,
            "raw_repeats": raw,
        })
    return rows


def measure(method, workload, repeats=5):
    return measure_methods((method,), workload, repeats)[0]


def workload_specs(sizes, counts, hit_rates, policies):
    """Skip unattainable exact hit rates, such as 50% for a single query."""
    return [(n, q, rate, policy)
            for n, q, rate, policy in itertools.product(sizes, counts, hit_rates, policies)
            if math.isclose(q * rate, round(q * rate), abs_tol=1e-9)]


def git_output(*args):
    result = subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def source_hashes():
    return {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            for name in ("algorithms.py", "data.py", "benchmark.py", "test_lab.py", "dashboard.py", "dashboard_template.html")}


def run(output, sizes, counts, hit_rates, policies, repeats, seed):
    cases = workload_specs(sizes, counts, hit_rates, policies)
    if not cases:
        raise ValueError("No feasible workload: query count must represent the requested hit rate exactly")
    settings = dict(sizes=sizes, query_counts=counts, hit_rates=hit_rates,
                    duplicate_policies=policies, repeats=repeats, base_seed=seed,
                    actual_workload_count=len(cases), exact_hit_rates_only=True)
    metadata = {
        "schema_version": 2,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "implementation": platform.python_implementation(),
        "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor(), "logical_cpus": os.cpu_count(),
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_status_at_measurement": git_output("status", "--short"),
        "source_sha256": source_hashes(), "settings": settings,
        "units": {"time": "milliseconds per complete invocation (one query batch)", "memory": "bytes"},
        "protocol": "timeit/perf_counter: one calibration/warm-up per phase/method/round, followed by grouped calls targeting 3 ms (maximum 20000 calls); at least five rounds; independently shuffled method order per round. Preparation and total rebuild state every call. Query phase reuses one index for that round. Preparation, batch and total are independent measurements and need not add up. Python call and temporary-result cleanup overhead included; cyclic GC disabled by timeit. Generation, validation, tracing and rendering excluded. All timing rounds for a workload finish before memory runs.",
        "memory_protocol": "Separate fresh tracemalloc run for each method/version/workload. Input and queries allocated before tracing; prepared structures and returned output retained at reading. Reports current and peak traced Python bytes, not process RSS or mathematical auxiliary space. No native-memory completeness claim.",
    }
    rows = []
    for index, (n, q, rate, policy) in enumerate(cases):
        work = make_workload(n, q, rate, seed + index, policy)
        rows.extend(measure_methods(METHODS, work, repeats, order_seed=seed + 100000 + index))
        print(f"Workload {index + 1}/{len(cases)}: n={n}, q={q}, hits={work.actual_hit_rate:g}, {policy}", flush=True)
    output.mkdir(parents=True, exist_ok=True)
    (output / "measurements.json").write_text(json.dumps({"metadata": metadata, "rows": rows}, indent=2) + "\n", encoding="utf-8")
    columns = [key for key in rows[0] if key != "raw_repeats"]
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({key: row[key] for key in columns} for row in rows)
    with (output / "raw_repeats.csv").open("w", newline="", encoding="utf-8") as stream:
        keys = ("method", "version", "n", "q", "requested_hit_rate", "actual_hit_rate", "duplicate_policy", "seed", "order_seed")
        writer = csv.DictWriter(stream, fieldnames=keys + ("repeat", "method_position") + TIME_KEYS + CALL_KEYS)
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
    if not workload_specs(args.sizes, args.query_counts, args.hit_rates, args.policies):
        parser.error("No query count can represent the requested hit rates exactly")
    run(args.output, args.sizes, args.query_counts, args.hit_rates, args.policies, args.repeats, args.seed)


if __name__ == "__main__":
    main()
