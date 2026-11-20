import argparse
import gc
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TypeAlias, cast

from algorithms.search import (
    binary_search as revised_binary_search,
    hash_membership as revised_hash_membership,
    linear_search as revised_linear_search,
)
from algorithms.search_v1 import (
    binary_search as original_binary_search,
    hash_membership as original_hash_membership,
    linear_search as original_linear_search,
)
from data.generate import GENERATOR_VERSION, generate_case


ROOT = Path(__file__).resolve().parents[1]
SIZES = (1_000, 10_000, 100_000)
QUERY_COUNTS = (1, 100)
REQUESTED_HIT_RATES = (0.0, 0.5, 1.0)
SEED_BASE = 20261120
SMOKE_SEED = 20261119
REPEAT_COUNT = 5
WARMUP_CALLS = 1
CALIBRATION_TARGET_SECONDS = 0.005
MAX_BATCH_CALLS = 2_048


SearchFunction: TypeAlias = Callable[[list[int], list[int]], list[bool]]
PreparedState: TypeAlias = list[int] | set[int]


@dataclass(frozen=True)
class MethodVersion:
    version: str
    method: str
    public_function: SearchFunction


METHODS = (
    MethodVersion("search_v1", "linear_search", original_linear_search),
    MethodVersion("search_v1", "binary_search", original_binary_search),
    MethodVersion("search_v1", "hash_membership", original_hash_membership),
    MethodVersion("search", "linear_search", revised_linear_search),
    MethodVersion("search", "binary_search", revised_binary_search),
    MethodVersion("search", "hash_membership", revised_hash_membership),
)


def _prepare_adapter(method: str, ids: list[int]) -> PreparedState:
    if method == "linear_search":
        return ids
    if method == "binary_search":
        return sorted(ids)
    if method == "hash_membership":
        return set(ids)
    raise ValueError(f"Unknown search method: {method}")


def _linear_query_adapter(ids: list[int], queries: list[int]) -> list[bool]:
    answers = []
    for query in queries:
        found = False
        for id_value in ids:
            if id_value == query:
                found = True
                break
        answers.append(found)
    return answers


def _recursive_contains(
    sorted_ids: list[int], query: int, left: int, right: int
) -> bool:
    if left > right:
        return False

    middle = (left + right) // 2
    middle_value = sorted_ids[middle]
    if middle_value == query:
        return True
    if query < middle_value:
        return _recursive_contains(sorted_ids, query, left, middle - 1)
    return _recursive_contains(sorted_ids, query, middle + 1, right)


def _recursive_binary_query_adapter(
    sorted_ids: list[int], queries: list[int]
) -> list[bool]:
    return [
        _recursive_contains(sorted_ids, query, 0, len(sorted_ids) - 1)
        for query in queries
    ]


def _iterative_binary_query_adapter(
    sorted_ids: list[int], queries: list[int]
) -> list[bool]:
    answers = []
    for query in queries:
        left = 0
        right = len(sorted_ids) - 1
        found = False

        while left <= right:
            middle = (left + right) // 2
            middle_value = sorted_ids[middle]
            if middle_value == query:
                found = True
                break
            if query < middle_value:
                right = middle - 1
            else:
                left = middle + 1

        answers.append(found)
    return answers


def _query_adapter(
    spec: MethodVersion, prepared: PreparedState, queries: list[int]
) -> list[bool]:
    if spec.method == "linear_search":
        if not isinstance(prepared, list):
            raise TypeError("Linear-search adapter expects the original ID list.")
        return _linear_query_adapter(prepared, queries)

    if spec.method == "binary_search":
        if not isinstance(prepared, list):
            raise TypeError("Binary-search adapter expects a sorted ID list.")
        if spec.version == "search_v1":
            return _recursive_binary_query_adapter(prepared, queries)
        return _iterative_binary_query_adapter(prepared, queries)

    if spec.method == "hash_membership":
        if not isinstance(prepared, set):
            raise TypeError("Hash-membership adapter expects a prepared set.")
        return [query in prepared for query in queries]

    raise ValueError(f"Unknown search method: {spec.method}")


def _verify_case(
    spec: MethodVersion,
    ids: list[int],
    queries: list[int],
    expected: list[bool],
) -> None:
    public_answers = spec.public_function(ids, queries)
    if public_answers != expected:
        raise AssertionError(
            f"{spec.version}.{spec.method} disagrees with generated answers."
        )

    prepared = _prepare_adapter(spec.method, ids)
    adapter_answers = _query_adapter(spec, prepared, queries)
    if adapter_answers != expected or adapter_answers != public_answers:
        raise AssertionError(
            f"{spec.version}.{spec.method} adapter disagrees with its "
            "public method or generated answers."
        )


def _discard_call(operation: Callable[[], object]) -> None:
    result = operation()
    del result


def _batch_elapsed(
    operation: Callable[[], object], call_count: int
) -> float:
    result: object | None = None
    started = time.perf_counter()
    for _ in range(call_count):
        result = operation()
    elapsed = time.perf_counter() - started
    del result
    return elapsed


def _calibrate_batch(operation: Callable[[], object]) -> tuple[int, bool]:
    call_count = 1
    while True:
        elapsed = _batch_elapsed(operation, call_count)

        if elapsed >= CALIBRATION_TARGET_SECONDS:
            return call_count, True
        if call_count >= MAX_BATCH_CALLS:
            return call_count, False
        call_count = min(call_count * 2, MAX_BATCH_CALLS)


def _time_average(
    operation: Callable[[], object], call_count: int
) -> float:
    return _batch_elapsed(operation, call_count) / call_count


def _benchmark_timing(
    spec: MethodVersion, ids: list[int], queries: list[int]
) -> dict[str, object]:
    prepare_operation = lambda: _prepare_adapter(spec.method, ids)
    query_state = _prepare_adapter(spec.method, ids)
    query_operation = lambda: _query_adapter(spec, query_state, queries)
    public_operation = lambda: spec.public_function(ids, queries)

    for operation in (prepare_operation, query_operation, public_operation):
        _discard_call(operation)

    prep_batch_count, prep_target_reached = _calibrate_batch(
        prepare_operation
    )
    query_batch_count, query_target_reached = _calibrate_batch(
        query_operation
    )
    public_batch_count, public_target_reached = _calibrate_batch(
        public_operation
    )

    prep_repeats = []
    query_repeats = []
    public_repeats = []
    combined_repeats = []
    for _ in range(REPEAT_COUNT):
        prep_seconds = _time_average(prepare_operation, prep_batch_count)
        query_seconds = _time_average(query_operation, query_batch_count)
        public_seconds = _time_average(public_operation, public_batch_count)
        prep_repeats.append(prep_seconds)
        query_repeats.append(query_seconds)
        public_repeats.append(public_seconds)
        combined_repeats.append(prep_seconds + query_seconds)

    del query_state
    return {
        "version": spec.version,
        "method": spec.method,
        "batch_counts": {
            "preparation_calls": prep_batch_count,
            "query_batch_calls": query_batch_count,
            "public_end_to_end_calls": public_batch_count,
        },
        "calibration_target_reached": {
            "preparation": prep_target_reached,
            "query_batch": query_target_reached,
            "public_end_to_end": public_target_reached,
        },
        "preparation_seconds_per_call_repeats": prep_repeats,
        "query_seconds_per_complete_batch_repeats": query_repeats,
        "component_total_seconds_per_repeat": combined_repeats,
        "public_end_to_end_seconds_per_call_repeats": public_repeats,
        "preparation_median_seconds_per_call": statistics.median(prep_repeats),
        "query_median_seconds_per_complete_batch": statistics.median(
            query_repeats
        ),
        "component_total_median_seconds": statistics.median(combined_repeats),
        "public_end_to_end_median_seconds_per_call": statistics.median(
            public_repeats
        ),
    }


def _measure_memory(
    spec: MethodVersion, ids: list[int], queries: list[int]
) -> tuple[list[bool], int, int]:
    if tracemalloc.is_tracing():
        raise RuntimeError("Memory measurement requires a fresh trace session.")

    gc.collect()
    tracemalloc.start()
    try:
        output = spec.public_function(ids, queries)
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return output, current_bytes, peak_bytes


def _fixed_workloads(smoke: bool) -> list[dict[str, object]]:
    if smoke:
        return [
            {
                "n": 64,
                "q": 8,
                "requested_hit_rate": 0.5,
                "seed": SMOKE_SEED,
            }
        ]

    workloads = []
    workload_index = 0
    for n in SIZES:
        for q in QUERY_COUNTS:
            for hit_rate in REQUESTED_HIT_RATES:
                workloads.append(
                    {
                        "n": n,
                        "q": q,
                        "requested_hit_rate": hit_rate,
                        "seed": SEED_BASE + workload_index,
                    }
                )
                workload_index += 1
    return workloads


def _git_metadata() -> dict[str, object]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status_text = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    status_lines = status_text.splitlines()
    return {
        "head": head,
        "dirty_working_tree": bool(status_lines),
        "status_porcelain": status_lines,
    }


def _file_hashes() -> dict[str, str]:
    relative_paths = (
        "algorithms/search.py",
        "algorithms/search_v1.py",
        "data/generate.py",
        "benchmarks/run_benchmarks.py",
    )
    return {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in relative_paths
    }


def _run(smoke: bool) -> dict[str, object]:
    started_at = datetime.now(timezone.utc).isoformat()
    git_state = _git_metadata()
    file_hashes = _file_hashes()
    workload_settings = _fixed_workloads(smoke)
    workload_records = []
    timing_records = []
    memory_records = []

    for settings in workload_settings:
        n = cast(int, settings["n"])
        q = cast(int, settings["q"])
        requested_hit_rate = cast(float, settings["requested_hit_rate"])
        seed = cast(int, settings["seed"])
        case = generate_case(n, q, requested_hit_rate, seed)
        ids = cast(list[int], case["ids"])
        queries = cast(list[int], case["queries"])
        expected = cast(list[bool], case["expected_answers"])
        generator_metadata = cast(dict[str, object], case["metadata"])
        actual_hit_count = cast(int, generator_metadata["actual_hit_count"])
        actual_hit_rate = cast(float | None, generator_metadata["actual_hit_rate"])
        genuinely_mixed = 0 < actual_hit_count < q
        workload_id = (
            f"n{n}_q{q}_hit{requested_hit_rate:g}_seed{seed}"
        )
        hit_rate_note = None
        if q == 1 and requested_hit_rate == 0.5:
            hit_rate_note = (
                "q=1 cannot represent a genuinely mixed 50% workload; "
                f"the achieved hit rate is {actual_hit_rate:.1%}."
            )

        workload_records.append(
            {
                "workload_id": workload_id,
                "n": n,
                "q": q,
                "seed": seed,
                "requested_hit_rate": requested_hit_rate,
                "actual_hit_count": actual_hit_count,
                "actual_hit_rate": actual_hit_rate,
                "genuinely_mixed": genuinely_mixed,
                "hit_rate_note": hit_rate_note,
                "duplicate_policy": generator_metadata["duplicate_policy"],
                "id_range": generator_metadata["id_range"],
                "absent_query_policy": generator_metadata[
                    "absent_query_policy"
                ],
                "generator_version": generator_metadata[
                    "generator_version"
                ],
            }
        )

        for spec in METHODS:
            _verify_case(spec, ids, queries, expected)
            timing = _benchmark_timing(spec, ids, queries)
            timing["workload_id"] = workload_id
            timing_records.append(timing)

            memory_output, current_bytes, peak_bytes = _measure_memory(
                spec, ids, queries
            )
            if memory_output != expected:
                raise AssertionError(
                    f"{spec.version}.{spec.method} failed its separate "
                    "memory-run correctness check."
                )
            memory_records.append(
                {
                    "workload_id": workload_id,
                    "version": spec.version,
                    "method": spec.method,
                    "output_length": len(memory_output),
                    "current_traced_bytes": current_bytes,
                    "peak_traced_bytes": peak_bytes,
                }
            )
            del memory_output

        del ids, queries, expected, case

    metadata = {
        "schema_version": 1,
        "run_mode": "smoke" if smoke else "full",
        "started_at_utc": started_at,
        "python_version": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "git": git_state,
        "sha256": file_hashes,
        "generator_version": GENERATOR_VERSION,
        "matrix": {
            "n_values": [64] if smoke else list(SIZES),
            "q_values": [8] if smoke else list(QUERY_COUNTS),
            "requested_hit_rates": (
                [0.5] if smoke else list(REQUESTED_HIT_RATES)
            ),
            "seed_base": SEED_BASE,
            "seed_policy": (
                "Full matrix seeds are SEED_BASE plus the zero-based workload "
                "index in n, q, hit-rate loop order; each actual seed is "
                "saved in its workload record."
            ),
            "smoke_seed": SMOKE_SEED,
            "versions_and_methods": [
                {"version": spec.version, "method": spec.method}
                for spec in METHODS
            ],
        },
        "timing": {
            "clock": "time.perf_counter",
            "unit": "seconds",
            "warmup_calls_per_operation": WARMUP_CALLS,
            "measured_repeats": REPEAT_COUNT,
            "calibration_target_seconds": CALIBRATION_TARGET_SECONDS,
            "maximum_batch_calls": MAX_BATCH_CALLS,
            "calibration_policy": (
                "For preparation, one complete query-batch adapter call, and "
                "a direct public call, start with one call and double the "
                "batch until it takes at least the target duration or reaches "
                "the call cap. The last return value remains alive until the "
                "timer stops; batch outputs are not accumulated. Calibration "
                "and warm-up are excluded from retained repeats."
            ),
            "preparation_definition": (
                "Adapter preparation is timed separately. Binary search "
                "constructs sorted(ids); hash membership constructs set(ids). "
                "Linear preparation returns the original IDs reference and "
                "performs no data copy. Each measured preparation call creates "
                "fresh state where applicable and discards it."
            ),
            "query_definition": (
                "Adapter query time is per complete ordered query batch of q "
                "queries, includes returned-list allocation, and is not per "
                "query. Query-only adapter calls reuse a prepared state built "
                "outside that component timer."
            ),
            "component_total_definition": (
                "For each repeat, add that repeat's preparation seconds per "
                "call and query seconds per complete batch; report the median "
                "of those five sums."
            ),
            "public_end_to_end_definition": (
                "Separately time the actual public method, including its own "
                "preparation, complete query batch, and output allocation. "
                "This is direct public-call timing, not the adapter-component "
                "sum."
            ),
            "adapter_note": (
                "Component timings measure benchmark adapters, not direct "
                "public method calls. Outside timing, each adapter's "
                "correctness-check output is compared with both its public "
                "method and generator-provided expected answers."
            ),
            "excluded_from_timing": [
                "input generation",
                "correctness checks",
                "warm-up and calibration",
                "printing",
                "file output",
                "memory tracing",
            ],
        },
        "memory": {
            "tool": "tracemalloc",
            "unit": "bytes",
            "separate_fresh_trace_per_method_version_workload": True,
            "public_method_includes_preparation": True,
            "input_allocations": "excluded; inputs are generated before tracing",
            "included_allocations": "preparation and returned output",
            "current_bytes_definition": (
                "Read while the returned output remains alive; temporary "
                "preparation structures may already have been freed."
            ),
            "peak_bytes_definition": (
                "Peak traced Python allocation during the public method call, "
                "including temporary preparation structures."
            ),
            "limitation": (
                "tracemalloc measures traced Python allocations, not total "
                "process memory or theoretical auxiliary space."
            ),
        },
        "workload_count": len(workload_records),
        "timing_record_count": len(timing_records),
        "memory_record_count": len(memory_records),
    }
    return {
        "metadata": metadata,
        "workloads": workload_records,
        "timing_results": timing_records,
        "memory_results": memory_records,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure the finance lab search methods."
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run a small fixed workload before the full matrix",
    )
    args = parser.parse_args(argv)

    default_name = (
        "benchmark_smoke.json" if args.smoke else "benchmark_results.json"
    )
    output_path = ROOT / "results" / default_name
    result = _run(args.smoke)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"Saved {result['metadata']['run_mode']} benchmark to {output_path}; "
        f"{result['metadata']['workload_count']} workloads, "
        f"{result['metadata']['timing_record_count']} timing records, "
        f"{result['metadata']['memory_record_count']} memory records."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
