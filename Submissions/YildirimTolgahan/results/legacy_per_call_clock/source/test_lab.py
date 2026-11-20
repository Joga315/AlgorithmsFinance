"""Shared specification tests for all three methods and both versions."""
import unittest
import json
from pathlib import Path
import statistics
import tempfile

from algorithms import METHODS, linear_search, binary_search_recursive, binary_search_iterative
from data import make_workload
from benchmark import measure
from dashboard import build


class SearchContractTests(unittest.TestCase):
    def check_case(self, items, queries, expected):
        for method in METHODS:
            with self.subTest(method=method.name, version=method.version, items=items, queries=queries):
                before_items, before_queries = items.copy(), queries.copy()
                result = method.answer(items, queries)
                self.assertIsInstance(result, list)
                self.assertEqual(result, expected)
                self.assertTrue(all(type(value) is bool for value in result))
                self.assertEqual(items, before_items)
                self.assertEqual(queries, before_queries)
                self.assertEqual(method.answer(items, queries), expected)

    def test_empty_array_and_queries(self):
        self.check_case([], [], [])
        self.check_case([], [0, -1, 7], [False, False, False])
        self.check_case([7], [], [])

    def test_one_entry(self):
        self.check_case([7], [7, 6, 8, 7], [True, False, False, True])

    def test_slide_example_and_order(self):
        self.check_case([7, 11, 7], [11, 9, 7], [True, False, True])

    def test_unsorted_input_duplicates_and_boundaries(self):
        self.check_case([11, -4, 7, 7, 0], [-5, -4, 0, 7, 11, 12], [False, True, True, True, True, False])
        self.check_case([4, 4, 4], [3, 4, 5], [False, True, False])

    def test_large_signed_integers(self):
        self.check_case([10**50, -(10**50), 0], [10**50, 1, -(10**50)], [True, False, True])

    def test_generated_inputs_against_independent_oracle(self):
        for n in (0, 1, 2, 17, 128):
            for policy in ("unique", "duplicates"):
                for rate in ((0.0,) if n == 0 else (0.0, 0.5, 1.0)):
                    workload = make_workload(n, 19, rate, seed=831, duplicate_policy=policy)
                    expected = [any(item == query for item in workload.items) for query in workload.queries]
                    self.check_case(workload.items, workload.queries, expected)

    def test_search_primitives(self):
        for function in (linear_search, binary_search_recursive, binary_search_iterative):
            for items in ([], [3], [-9, 0], [-9, 0, 3, 3, 10]):
                for query in (-10, -9, 0, 3, 10, 11):
                    with self.subTest(function=function.__name__, items=items, query=query):
                        self.assertIs(function(items, query), query in items)


class GeneratorTests(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(make_workload(100, 30, 0.5, 12), make_workload(100, 30, 0.5, 12))

    def test_sizes_hit_rates_and_policies(self):
        for policy in ("unique", "duplicates"):
            for rate in (0, 0.5, 1):
                work = make_workload(100, 100, rate, 12, policy)
                self.assertEqual((len(work.items), len(work.queries)), (100, 100))
                self.assertEqual(work.actual_hit_rate, rate)
                if policy == "unique":
                    self.assertEqual(len(set(work.items)), 100)
                else:
                    self.assertLess(len(set(work.items)), 100)

    def test_invalid_settings(self):
        for args in ((-1, 3, 0), (1, -1, 0), (1, 3, -0.1), (1, 3, 1.1), (0, 3, 1), (3, 3, 0.5, 0, "unknown")):
            with self.assertRaises(ValueError):
                make_workload(*args)


class MeasurementTests(unittest.TestCase):
    def test_raw_repeats_and_memory_contract(self):
        for method in METHODS:
            with self.subTest(method=method.name, version=method.version):
                row = measure(method, make_workload(17, 9, 0.5), repeats=5)
                self.assertEqual(len(row["raw_repeats"]), 5)
                self.assertGreaterEqual(row["peak_traced_bytes"], row["current_traced_bytes"])
                for sample in row["raw_repeats"]:
                    self.assertGreaterEqual(sample["calls"], 1)
                    self.assertGreaterEqual(sample["preparation_ms"], 0)
                    self.assertGreaterEqual(sample["query_batch_ms"], 0)
                    self.assertAlmostEqual(sample["total_ms"], sample["preparation_ms"] + sample["query_batch_ms"], places=9)
                for key in ("preparation_ms", "query_batch_ms", "total_ms"):
                    self.assertEqual(row[key], statistics.median(sample[key] for sample in row["raw_repeats"]))

    def test_too_few_repeats_rejected(self):
        with self.assertRaises(ValueError):
            measure(METHODS[0], make_workload(10, 1, 0), repeats=4)

    def test_dashboard_embeds_saved_data_without_executing_benchmarks(self):
        data = {"metadata": {"note": "</script><script>example</script>"},
                "rows": [{"method": "linear", "total_ms": 0.125}]}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            source, output = Path(folder) / "measurements.json", Path(folder) / "dashboard.html"
            source.write_text(json.dumps(data), encoding="utf-8")
            build(source, output)
            page = output.read_text(encoding="utf-8")
            payload = page.split('<script type="application/json" id="dataset">', 1)[1].split('</script>', 1)[0]
            self.assertEqual(json.loads(payload), data)
            self.assertNotIn("__DATA__", page)
            self.assertNotIn("__JSON_LINK__", page)


if __name__ == "__main__":
    unittest.main()
