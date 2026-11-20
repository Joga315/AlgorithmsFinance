import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


RESULTS_PATH = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "benchmark_results.json"
)

METHOD_LABELS = {
    "linear_search": "Linear search",
    "binary_search": "Binary search",
    "hash_membership": "Hash membership",
}
VERSION_LABELS = {
    "search_v1": "Original (recursive)",
    "search": "Revised (iterative)",
}
TIMING_METRICS = (
    (
        "Preparation",
        "preparation_median_ms",
        "Preparation median (ms per call)",
    ),
    (
        "Complete query batch",
        "query_batch_median_ms",
        "Query-batch median (ms per complete batch)",
    ),
    (
        "Combined components",
        "component_total_median_ms",
        "Component-total median (ms)",
    ),
    (
        "Public end-to-end",
        "public_end_to_end_median_ms",
        "Public-method median (ms per call)",
    ),
)


@st.cache_data(show_spinner=False)
def _load_results(
    path: str, modified_ns: int, file_size: int
) -> tuple[dict[str, Any], bytes]:
    del modified_ns, file_size
    raw_json = Path(path).read_bytes()
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        raise ValueError("Benchmark results must be a JSON object.")
    return parsed, raw_json


def _validate_schema(results: dict[str, Any]) -> None:
    required = {"metadata", "workloads", "timing_results", "memory_results"}
    missing = required.difference(results)
    if missing:
        raise ValueError(
            "Benchmark results are missing required sections: "
            + ", ".join(sorted(missing))
        )
    for key in ("workloads", "timing_results", "memory_results"):
        if not isinstance(results[key], list):
            raise ValueError(f"Benchmark results section {key!r} must be a list.")


def _selected_timing_records(
    results: dict[str, Any],
    query_count: int,
    requested_hit_rate: float,
    versions: list[str],
    methods: list[str],
) -> list[dict[str, Any]]:
    workloads = {
        row["workload_id"]: row
        for row in results["workloads"]
        if row["q"] == query_count
        and row["requested_hit_rate"] == requested_hit_rate
    }
    return [
        {"timing": row, "workload": workloads[row["workload_id"]]}
        for row in results["timing_results"]
        if row["workload_id"] in workloads
        and row["version"] in versions
        and row["method"] in methods
    ]


def _display_timing_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display_rows = []
    for entry in records:
        timing = entry["timing"]
        workload = entry["workload"]
        display_rows.append(
            {
                "n": workload["n"],
                "version": timing["version"],
                "version_label": VERSION_LABELS[timing["version"]],
                "method": timing["method"],
                "method_label": METHOD_LABELS[timing["method"]],
                "series": (
                    f"{METHOD_LABELS[timing['method']]} — "
                    f"{VERSION_LABELS[timing['version']]}"
                ),
                "preparation_median_ms": (
                    timing["preparation_median_seconds_per_call"] * 1_000
                ),
                "query_batch_median_ms": (
                    timing["query_median_seconds_per_complete_batch"] * 1_000
                ),
                "component_total_median_ms": (
                    timing["component_total_median_seconds"] * 1_000
                ),
                "public_end_to_end_median_ms": (
                    timing["public_end_to_end_median_seconds_per_call"]
                    * 1_000
                ),
            }
        )
    return sorted(
        display_rows,
        key=lambda row: (row["n"], row["version"], row["method"]),
    )


def _chart_frame(
    display_rows: list[dict[str, Any]], metric_key: str
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "n": row["n"],
                "Series": row["series"],
                "Median (ms)": row[metric_key],
            }
            for row in display_rows
        ]
    )


def _memory_rows(
    results: dict[str, Any],
    query_count: int,
    requested_hit_rate: float,
    versions: list[str],
    methods: list[str],
) -> list[dict[str, Any]]:
    workloads = {
        row["workload_id"]: row
        for row in results["workloads"]
        if row["q"] == query_count
        and row["requested_hit_rate"] == requested_hit_rate
    }
    rows = []
    for row in results["memory_results"]:
        workload = workloads.get(row["workload_id"])
        if (
            workload is None
            or row["version"] not in versions
            or row["method"] not in methods
        ):
            continue
        rows.append(
            {
                "workload_id": workload["workload_id"],
                "n": workload["n"],
                "q": workload["q"],
                "requested_hit_rate": workload["requested_hit_rate"],
                "actual_hit_rate": workload["actual_hit_rate"],
                "version": row["version"],
                "method": row["method"],
                "current_traced_bytes": row["current_traced_bytes"],
                "peak_traced_bytes": row["peak_traced_bytes"],
            }
        )
    return sorted(rows, key=lambda row: (row["n"], row["version"], row["method"]))


def _raw_timing_rows(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for entry in records:
        timing = entry["timing"]
        workload = entry["workload"]
        batch_counts = timing["batch_counts"]
        rows.append(
            {
                "workload_id": workload["workload_id"],
                "n": workload["n"],
                "version": timing["version"],
                "method": timing["method"],
                "preparation_repeats_seconds_per_call": timing[
                    "preparation_seconds_per_call_repeats"
                ],
                "query_repeats_seconds_per_complete_batch": timing[
                    "query_seconds_per_complete_batch_repeats"
                ],
                "component_total_repeats_seconds": timing[
                    "component_total_seconds_per_repeat"
                ],
                "public_end_to_end_repeats_seconds_per_call": timing[
                    "public_end_to_end_seconds_per_call_repeats"
                ],
                "preparation_batch_calls": batch_counts[
                    "preparation_calls"
                ],
                "query_batch_calls": batch_counts["query_batch_calls"],
                "public_end_to_end_batch_calls": batch_counts[
                    "public_end_to_end_calls"
                ],
            }
        )
    return rows


def _render_chart(
    display_rows: list[dict[str, Any]],
    title: str,
    metric_key: str,
    y_label: str,
) -> None:
    st.subheader(title)
    if not display_rows:
        st.info("No measurements match the selected filters.")
        return
    st.line_chart(
        _chart_frame(display_rows, metric_key),
        x="n",
        y="Median (ms)",
        color="Series",
        x_label="Input length n",
        y_label=y_label,
    )


def main() -> None:
    st.set_page_config(
        page_title="Algorithms in Finance — Runtime Dashboard",
        layout="wide",
    )
    st.title("Algorithms in Finance — Runtime Dashboard")
    st.caption(
        "Displays saved benchmark results only. Changing filters never reruns "
        "the benchmark."
    )

    if not RESULTS_PATH.is_file():
        st.error("Benchmark results are missing.")
        st.write("From the submission directory, generate them with:")
        st.code("python -m benchmarks.run_benchmarks", language="powershell")
        st.stop()

    try:
        file_stat = RESULTS_PATH.stat()
        results, raw_json = _load_results(
            str(RESULTS_PATH), file_stat.st_mtime_ns, file_stat.st_size
        )
        _validate_schema(results)
    except (OSError, ValueError) as error:
        st.error(f"Could not load benchmark results: {error}")
        st.stop()

    workloads = results["workloads"]
    query_options = sorted({row["q"] for row in workloads})
    hit_rate_options = sorted(
        {row["requested_hit_rate"] for row in workloads}
    )
    version_options = list(
        dict.fromkeys(row["version"] for row in results["timing_results"])
    )
    method_options = list(
        dict.fromkeys(row["method"] for row in results["timing_results"])
    )

    columns = st.columns(4)
    with columns[0]:
        default_q = 100 if 100 in query_options else query_options[0]
        query_count = st.selectbox(
            "Query count q",
            query_options,
            index=query_options.index(default_q),
            key="query_count",
        )
    with columns[1]:
        default_rate = 0.5 if 0.5 in hit_rate_options else hit_rate_options[0]
        requested_hit_rate = st.selectbox(
            "Requested hit rate",
            hit_rate_options,
            index=hit_rate_options.index(default_rate),
            format_func=lambda value: f"{value:.0%}",
            key="requested_hit_rate",
        )
    with columns[2]:
        selected_versions = st.multiselect(
            "Versions",
            version_options,
            default=version_options,
            format_func=lambda value: VERSION_LABELS.get(value, value),
            key="versions",
        )
    with columns[3]:
        selected_methods = st.multiselect(
            "Methods",
            method_options,
            default=method_options,
            format_func=lambda value: METHOD_LABELS.get(value, value),
            key="methods",
        )

    matching_workloads = [
        row
        for row in workloads
        if row["q"] == query_count
        and row["requested_hit_rate"] == requested_hit_rate
    ]
    achieved_rates = {
        row["actual_hit_rate"] for row in matching_workloads
    }
    if len(achieved_rates) == 1:
        achieved_rate = next(iter(achieved_rates))
        displayed_rate = (
            "N/A" if achieved_rate is None else f"{achieved_rate:.1%}"
        )
    else:
        displayed_rate = "Varies by workload"
    st.metric("Achieved hit rate", displayed_rate)
    if query_count == 1 and requested_hit_rate == 0.5:
        recorded_rate = displayed_rate
        st.warning(
            "For q=1 and a requested 50% hit rate, the saved workload "
            f"achieves {recorded_rate}. A single query is not a mixed-query "
            "workload."
        )

    selected_records = _selected_timing_records(
        results,
        query_count,
        requested_hit_rate,
        selected_versions,
        selected_methods,
    )
    display_rows = _display_timing_rows(selected_records)

    st.info(
        "Component totals sum separately timed adapter preparation and "
        "complete query-batch measurements. Public end-to-end values are "
        "direct calls to the public methods and include their own preparation; "
        "these are different measurement procedures."
    )
    for title, metric_key, metric_label in TIMING_METRICS:
        _render_chart(display_rows, title, metric_key, metric_label)

    median_columns = [
        "n",
        "version_label",
        "method_label",
        "preparation_median_ms",
        "query_batch_median_ms",
        "component_total_median_ms",
        "public_end_to_end_median_ms",
    ]
    st.subheader("Displayed median timings (milliseconds)")
    if display_rows:
        st.dataframe(
            pd.DataFrame(display_rows)[median_columns],
            hide_index=True,
        )
    else:
        st.info("No timing rows match the selected filters.")

    with st.expander("Memory measurements"):
        st.write(
            "Input allocations are excluded. Preparation and returned-output "
            "allocations are included. Current traced bytes are read while "
            "the output is alive, after temporary preparation structures may "
            "have been freed; peak bytes capture their traced high-water mark. "
            "tracemalloc measures Python allocations, not total process memory "
            "or theoretical auxiliary space."
        )
        memory_rows = _memory_rows(
            results,
            query_count,
            requested_hit_rate,
            selected_versions,
            selected_methods,
        )
        st.dataframe(pd.DataFrame(memory_rows), hide_index=True)

    with st.expander("Raw timing repeats and batching"):
        st.caption(
            "Repeat arrays remain in seconds. Query repeats are per complete "
            "query batch, not per query."
        )
        st.dataframe(
            pd.DataFrame(_raw_timing_rows(selected_records)),
            hide_index=True,
        )

    with st.expander("Environment, seeds, policies, and code hashes"):
        st.json(results["metadata"])
        st.dataframe(pd.DataFrame(workloads), hide_index=True)

    st.download_button(
        "Download original benchmark_results.json",
        data=raw_json,
        file_name=RESULTS_PATH.name,
        mime="application/json",
    )
    st.caption(
        "The dashboard presents recorded measurements and makes no claim "
        "that one version is faster."
    )


if __name__ == "__main__":
    main()
