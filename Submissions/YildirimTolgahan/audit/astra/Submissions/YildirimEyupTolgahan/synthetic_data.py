"""Seeded workloads with exact hit counts and controlled duplicates."""
from random import Random


def generate_data(n, query_count, hits, seed=42):
    if n < 0 or not 0 <= hits <= query_count or (hits and not n):
        raise ValueError("Require n >= 0, 0 <= hits <= query_count and IDs for hits")
    rng = Random(seed)
    # Sampling from a bounded domain permits duplicates. Odd misses stay in range.
    domain = max(1, n)
    ids = [2 * rng.randrange(domain) for _ in range(n)]
    queries = [rng.choice(ids) for _ in range(hits)]
    queries.extend(2 * rng.randrange(domain) + 1 for _ in range(query_count - hits))
    rng.shuffle(queries)
    return ids, queries
