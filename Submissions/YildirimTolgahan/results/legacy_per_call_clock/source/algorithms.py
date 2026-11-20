"""Own linear/binary search; standard-library sorting and hash sets are allowed."""
from dataclasses import dataclass
from typing import Callable


def linear_search(items, query):
    for item in items:
        if item == query:
            return True
    return False


def binary_search_recursive(items, query):
    """Search an already sorted sequence; use indices rather than slices."""
    return _recursive_interval(items, query, 0, len(items) - 1)


def _recursive_interval(items, query, left, right):
    if left > right:
        return False
    middle = (left + right) // 2
    if items[middle] == query:
        return True
    if items[middle] < query:
        return _recursive_interval(items, query, middle + 1, right)
    return _recursive_interval(items, query, left, middle - 1)


def binary_search_iterative(items, query):
    """Search the inclusive interval [left, right] in an already sorted sequence."""
    left, right = 0, len(items) - 1
    while left <= right:
        middle = (left + right) // 2
        if items[middle] == query:
            return True
        if items[middle] < query:
            left = middle + 1
        else:
            right = middle - 1
    return False


def unchanged(items):
    return items


def hash_contains(prepared, query):
    return query in prepared


@dataclass(frozen=True)
class Method:
    name: str
    version: str
    prepare: Callable
    contains: Callable

    def answer(self, items, queries):
        prepared = self.prepare(items)
        return [self.contains(prepared, query) for query in queries]


METHODS = (
    Method("linear", "original", list, linear_search),
    Method("linear", "revised", unchanged, linear_search),
    Method("binary", "original", sorted, binary_search_recursive),
    Method("binary", "revised", sorted, binary_search_iterative),
    Method("hash_set", "original", set, hash_contains),
    Method("hash_set", "revised", set, hash_contains),
)
