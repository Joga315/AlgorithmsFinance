"""Tests written before the implementation. Run with:  python -m pytest -q

Every method must pass exactly the same tests.
"""
import random

import pytest

from data import make_ids, make_queries
from membership import METHODS, run

ALL = list(METHODS)


def expected(ids, queries):
    """Independent reference answer (Python's own `in` on a list)."""
    return [x in ids for x in queries]


@pytest.mark.parametrize("method", ALL)
def test_slide_example(method):
    assert run(method, [7, 11, 7], [11, 9, 7]) == [True, False, True]


@pytest.mark.parametrize("method", ALL)
def test_empty_array(method):
    assert run(method, [], [1, 2, 3]) == [False, False, False]


@pytest.mark.parametrize("method", ALL)
def test_empty_queries(method):
    assert run(method, [7, 11], []) == []


@pytest.mark.parametrize("method", ALL)
def test_both_empty(method):
    assert run(method, [], []) == []


@pytest.mark.parametrize("method", ALL)
def test_one_entry(method):
    assert run(method, [5], [5, 4, 6]) == [True, False, False]


@pytest.mark.parametrize("method", ALL)
def test_duplicates(method):
    assert run(method, [3, 3, 3, 1], [3, 1, 2]) == [True, True, False]


@pytest.mark.parametrize("method", ALL)
def test_unsorted_input(method):
    assert run(method, [9, 1, 8, 2, 7], [7, 9, 1, 5]) == [True, True, True, False]


@pytest.mark.parametrize("method", ALL)
def test_first_and_last_positions(method):
    ids = [4, 8, 15, 16, 23, 42]
    assert run(method, ids, [4, 42]) == [True, True]


@pytest.mark.parametrize("method", ALL)
def test_smaller_and_larger_than_all(method):
    assert run(method, [10, 20, 30], [-5, 0, 99]) == [False, False, False]


@pytest.mark.parametrize("method", ALL)
def test_negative_ids(method):
    assert run(method, [-3, 0, -7], [-7, 3]) == [True, False]


@pytest.mark.parametrize("method", ALL)
def test_output_order_and_repeated_queries(method):
    queries = [2, 1, 2, 3, 1]
    assert run(method, [1, 2], queries) == [True, True, True, False, True]


@pytest.mark.parametrize("method", ALL)
def test_input_unchanged(method):
    ids = [7, 2, 11, 4]
    queries = [11, 3]
    run(method, ids, queries)
    assert ids == [7, 2, 11, 4]
    assert queries == [11, 3]


@pytest.mark.parametrize("method", ALL)
def test_repeated_calls_give_same_answer(method):
    ids, queries = [5, 1, 9], [9, 2]
    assert run(method, ids, queries) == run(method, ids, queries)


@pytest.mark.parametrize("method", ALL)
@pytest.mark.parametrize("dup", ["none", "allowed"])
@pytest.mark.parametrize("hit", [0.0, 0.5, 1.0])
def test_synthetic_against_reference(method, dup, hit):
    ids = make_ids(500, seed=1, duplicates=dup)
    queries = make_queries(ids, 200, hit, seed=1)
    assert run(method, ids, queries) == expected(ids, queries)


@pytest.mark.parametrize("method", ALL)
def test_random_small_cases(method):
    rng = random.Random(2026)
    for _ in range(300):
        ids = [rng.randint(-5, 5) for _ in range(rng.randint(0, 12))]
        queries = [rng.randint(-6, 6) for _ in range(rng.randint(0, 8))]
        assert run(method, ids, queries) == expected(ids, queries)


def test_generator_hit_rate_is_exact():
    ids = make_ids(1000, seed=3)
    queries = make_queries(ids, 100, 0.5, seed=3)
    hits = sum(x in set(ids) for x in queries)
    assert hits == 50
    assert all(x % 2 == 1 for x in queries if x not in set(ids))


def test_generator_is_reproducible():
    assert make_ids(100, seed=9) == make_ids(100, seed=9)
    a = make_queries(make_ids(100, seed=9), 20, 0.5, seed=9)
    b = make_queries(make_ids(100, seed=9), 20, 0.5, seed=9)
    assert a == b
