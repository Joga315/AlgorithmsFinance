"""Membership-query algorithms sharing one public specification."""

from typing import List, Sequence


def linear_search(ids: Sequence[int], queries: Sequence[int]) -> List[bool]:
    """Search the ID array from left to right for every ordered query."""
    results = []

    for query in queries:
        found = False
        for candidate in ids:
            if candidate == query:
                found = True
                break
        results.append(found)

    return results


def _recursive_binary_contains(
    sorted_ids: Sequence[int], query: int, low: int, high: int
) -> bool:
    """Return whether one query occurs between inclusive bounds."""
    if low > high:
        return False

    middle = low + (high - low) // 2
    middle_value = sorted_ids[middle]

    if middle_value == query:
        return True
    if query < middle_value:
        return _recursive_binary_contains(sorted_ids, query, low, middle - 1)
    return _recursive_binary_contains(sorted_ids, query, middle + 1, high)


def binary_search_recursive(
    ids: Sequence[int], queries: Sequence[int]
) -> List[bool]:
    """Original version: sort a copy, then use recursive binary search."""
    sorted_ids = sorted(ids)
    final_index = len(sorted_ids) - 1

    return [
        _recursive_binary_contains(sorted_ids, query, 0, final_index)
        for query in queries
    ]
def binary_search_iterative(
    ids: Sequence[int], queries: Sequence[int]
) -> List[bool]:
    """Revised version: sort a copy, then use iterative binary search."""
    sorted_ids = sorted(ids)
    results = []

    for query in queries:
        low = 0
        high = len(sorted_ids) - 1
        found = False

        while low <= high:
            middle = low + (high - low) // 2
            middle_value = sorted_ids[middle]

            if middle_value == query:
                found = True
                break
            if query < middle_value:
                high = middle - 1
            else:
                low = middle + 1

        results.append(found)

    return results

def binary_search(ids: Sequence[int], queries: Sequence[int]) -> List[bool]:
    """Run the current binary-search version using the shared interface."""
    return binary_search_iterative(ids, queries)


def hash_set_search(ids: Sequence[int], queries: Sequence[int]) -> List[bool]:
    """Build a standard-library hash set, then answer ordered queries."""
    id_set = set(ids)
    return [query in id_set for query in queries]
