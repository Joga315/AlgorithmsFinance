"""Reproducible integer IDs and ordered query batches, outside measurement."""
from dataclasses import dataclass
import random


@dataclass
class Workload:
    items: list[int]
    queries: list[int]
    seed: int
    requested_hit_rate: float
    duplicate_policy: str

    @property
    def actual_hit_rate(self):
        present = set(self.items)
        return sum(query in present for query in self.queries) / len(self.queries) if self.queries else 0.0


def make_workload(n, q, hit_rate, seed=2026, duplicate_policy="unique"):
    if n < 0 or q < 0 or not 0 <= hit_rate <= 1:
        raise ValueError("Require n,q >= 0 and 0 <= hit_rate <= 1")
    if duplicate_policy not in ("unique", "duplicates"):
        raise ValueError("Unknown duplicate policy")
    rng = random.Random(seed)
    if duplicate_policy == "unique":
        items = [2 * i for i in range(n)]
    else:
        items = [2 * rng.randrange(max(1, n // 4)) for _ in range(n)]
    rng.shuffle(items)
    hits = int(q * hit_rate + 0.5)
    if hits and not items:
        raise ValueError("Cannot generate present queries for an empty array")
    queries = [rng.choice(items) for _ in range(hits)]
    queries += [2 * rng.randrange(max(1, n)) + 1 for _ in range(q - hits)]
    rng.shuffle(queries)
    return Workload(items, queries, seed, hit_rate, duplicate_policy)
