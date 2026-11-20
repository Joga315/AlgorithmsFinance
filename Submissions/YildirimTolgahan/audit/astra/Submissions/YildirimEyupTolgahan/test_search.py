import itertools
import unittest

from searches import METHODS
from synthetic_data import generate_data


class MembershipTests(unittest.TestCase):
    def check_case(self, ids, queries, expected):
        for (name, version), (prepare, lookup) in METHODS.items():
            with self.subTest(method=name, version=version, ids=ids, queries=queries):
                data, batch = ids.copy(), queries.copy()
                prepared = prepare(data)
                for _ in range(2):
                    result = lookup(prepared, batch)
                    self.assertEqual(result, expected)
                    self.assertTrue(all(type(item) is bool for item in result))
                    self.assertEqual(data, ids)
                    self.assertEqual(batch, queries)

    def test_slide_example(self):
        self.check_case([7, 11, 7], [11, 9, 7], [True, False, True])

    def test_empty_batch(self):
        self.check_case([8], [], [])
        self.check_case([], [], [])

    def test_exhaustive_small_arrays(self):
        queries = [-2, 1, 0, -1, 2, 1]
        for size in range(5):
            for values in itertools.product((-1, 0, 1), repeat=size):
                self.check_case(list(values), queries, [q in values for q in queries])

    def test_generator(self):
        for n, q, hits in [(0, 0, 0), (0, 3, 0), (32, 20, 0),
                           (32, 20, 7), (32, 20, 20)]:
            ids, queries = generate_data(n, q, hits)
            self.assertEqual((len(ids), len(queries)), (n, q))
            self.assertEqual(sum(x in ids for x in queries), hits)
            self.assertEqual(generate_data(n, q, hits), (ids, queries))
        for case in [(-1, 1, 0), (2, 1, 2), (0, 1, 1)]:
            with self.assertRaises(ValueError):
                generate_data(*case)
