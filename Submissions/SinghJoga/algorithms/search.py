def linear_search(ids: list[int], queries: list[int]) -> list[bool]:
    """Return one actual bool per ordered integer query for an integer ID list.

    Preserve query order and leave both input lists unchanged.
    """
    results = []
    for query in queries:
        found = False
        for id_value in ids:
            if id_value == query:
                found = True
                break
        results.append(found)
    return results


def binary_search(ids: list[int], queries: list[int]) -> list[bool]:
    """Return one actual bool per ordered integer query for an integer ID list.

    Preserve query order and leave both input lists unchanged. Iteratively
    search a sorted copy of ``ids``.
    """
    sorted_ids = sorted(ids)
    results = []
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

        results.append(found)
    return results


def hash_membership(ids: list[int], queries: list[int]) -> list[bool]:
    """Return one actual bool per ordered integer query for an integer ID list.

    Preserve query order and leave both input lists unchanged.
    """
    id_set = set(ids)
    return [query in id_set for query in queries]
