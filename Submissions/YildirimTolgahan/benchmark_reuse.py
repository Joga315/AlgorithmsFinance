"""Compare rebuilding a hash index per batch with building once for all batches."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import statistics
import sys

from algorithms import HashIndex
from benchmark import timed_phase
from data import make_workload

HERE = Path(__file__).resolve().parent


def run(output, n=100000, q=100, batch_count=5, repeats=5):
    if min(n, q, batch_count) < 1 or repeats < 5:
        raise ValueError("Use positive sizes and at least five repeats")
    work = make_workload(n, q, 0.5, seed=721)
    batches = [work.queries[i % q:] + work.queries[:i % q] for i in range(batch_count)]
    present = set(work.items)
    expected = [[query in present for query in batch] for batch in batches]

    def rebuild():
        return [HashIndex(work.items).answer(batch) for batch in batches]

    def reuse():
        index = HashIndex(work.items)
        return [index.answer(batch) for batch in batches]

    operations = {"rebuild_each_batch": rebuild, "build_once": reuse}
    raw = {name: [] for name in operations}
    rng = random.Random(721)
    for repeat in range(1, repeats + 1):
        order = list(operations)
        rng.shuffle(order)
        for position, name in enumerate(order, 1):
            operation = operations[name]
            if operation() != expected:
                raise AssertionError("Incorrect reuse result")
            ms, calls = timed_phase(operation)
            if operation() != expected:
                raise AssertionError("Incorrect post-timing reuse result")
            raw[name].append({"repeat": repeat, "position": position, "ms": ms, "calls": calls})
    result = {
        "metadata": {"created_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version,
                     "platform": platform.platform(), "n": n, "q": q, "batch_count": batch_count,
                     "repeats": repeats, "seed": 721, "actual_hit_rate": work.actual_hit_rate,
                     "protocol": "Same fixed IDs and ordered batches; grouped timeit; median of five or more shuffled rounds. Both scenarios include all lookups and index construction: once overall versus once per batch. Data generation and validation excluded. Milliseconds per complete multi-batch execution.",
                     "source_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                       for name in ("algorithms.py", "data.py", "benchmark.py", "benchmark_reuse.py")}},
        "scenarios": {name: {"median_ms": statistics.median(s["ms"] for s in samples), "raw_repeats": samples}
                      for name, samples in raw.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({name: entry["median_ms"] for name, entry in result["scenarios"].items()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "results/reuse.json")
    parser.add_argument("--size", type=int, default=100000)
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--batches", type=int, default=5)
    args = parser.parse_args()
    run(args.output, args.size, args.queries, args.batches)
