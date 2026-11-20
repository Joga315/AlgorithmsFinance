"""Each registry entry exposes prepare(ids) and lookup(prepared, queries)."""


def use_input(ids):
    return ids


def linear_contains(ids, query):
    for value in ids:
        if value == query:
            return True
    return False


def linear_batch(ids, queries):
    return [linear_contains(ids, query) for query in queries]


def recursive_contains(ids, query, lo, hi):
    if lo >= hi:
        return False
    mid = (lo + hi) // 2
    if ids[mid] == query:
        return True
    if ids[mid] < query:
        return recursive_contains(ids, query, mid + 1, hi)
    return recursive_contains(ids, query, lo, mid)


def recursive_batch(ids, queries):
    return [recursive_contains(ids, query, 0, len(ids)) for query in queries]


def hash_batch(index, queries):
    return [query in index for query in queries]


ORIGINAL = {
    "linear": (use_input, linear_batch),
    "binary": (sorted, recursive_batch),
    "hash": (set, hash_batch),
}
METHODS = {(name, "original"): pair for name, pair in ORIGINAL.items()}


def iterative_contains(ids, query):
    lo, hi = 0, len(ids)
    while lo < hi:
        mid = (lo + hi) // 2
        if ids[mid] == query:
            return True
        if ids[mid] < query:
            lo = mid + 1
        else:
            hi = mid
    return False


def iterative_batch(ids, queries):
    return [iterative_contains(ids, query) for query in queries]


# Linear and hash are controls. Only the binary search procedure changes.
REVISED = {**ORIGINAL, "binary": (sorted, iterative_batch)}
METHODS.update({(name, "revised"): pair for name, pair in REVISED.items()})
