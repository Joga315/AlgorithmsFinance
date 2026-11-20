"""Generate raw timing and allocation records with Python's standard library."""
import csv
import hashlib
import json
import os
import platform
import random
import sys
import tracemalloc
from pathlib import Path
from timeit import Timer

from searches import METHODS
from synthetic_data import generate_data

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SEED = 42
REPEATS = 5


def save_csv(name, rows):
    with (RESULTS / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def timed(operation):
    timer = Timer(operation)
    elapsed = timer.timeit(1)  # warm up and calibrate outside the recorded sample
    calls = min(20000, max(1, int(0.003 / max(elapsed, 1e-9))))
    return timer.timeit(calls) / calls, calls


def benchmark():
    RESULTS.mkdir(exist_ok=True)
    times, memory = [], []
    order = random.Random(SEED)
    for n in (1000, 10000, 100000):
        for q in (1, 100):
            for hits in sorted({0, q // 2, q}):
                ids, queries = generate_data(n, q, hits, seed=SEED)
                expected = [x in ids for x in queries]
                methods = list(METHODS)
                for repeat in range(1, REPEATS + 1):
                    order.shuffle(methods)
                    for name, version in methods:
                        prepare, lookup = METHODS[name, version]
                        key = dict(n=n, q=q, hits=hits, hit_rate=hits/q, seed=SEED,
                                   method=name, version=version)
                        prepared = prepare(ids)
                        assert lookup(prepared, queries) == expected
                        operations = {
                            "prepare": lambda: prepare(ids),
                            "batch": lambda: lookup(prepared, queries),
                            "total": lambda: lookup(prepare(ids), queries),
                        }
                        for phase, operation in operations.items():
                            seconds, calls = timed(operation)
                            times.append(dict(**key, repeat=repeat, phase=phase,
                                              seconds=seconds, calls=calls))
                        del prepared
                        if repeat == 1:
                            tracemalloc.start()
                            index = prepare(ids)
                            output = lookup(index, queries)
                            current, peak = tracemalloc.get_traced_memory()
                            tracemalloc.stop()
                            memory.append(dict(**key, current_bytes=current, peak_bytes=peak))
                            del index, output
    save_csv("timings.csv", times)
    save_csv("memory.csv", memory)
    files = ("searches.py", "synthetic_data.py", "benchmark.py")
    metadata = dict(python=sys.version, os=platform.platform(), machine=platform.machine(),
                    logical_cpus=os.cpu_count(), processor=platform.processor() or "unreported",
                    seed=SEED, repeats=REPEATS, timer="timeit / perf_counter, seconds",
                    duplicate_policy="n draws with replacement from n even IDs",
                    source_sha256={f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
                                   for f in files})
    (RESULTS / "environment.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"Saved {len(times)} timing and {len(memory)} allocation records.")


if __name__ == "__main__":
    benchmark()
