"""Synthetic data generator, kept separate from algorithms and measurement.

IDs are drawn from EVEN integers, so any ODD integer is guaranteed absent.
This makes the hit rate of a query batch exact and checkable.
"""
import random


def make_ids(n, seed, duplicates="none"):
    """n integer trade IDs in random order.

    duplicates="none":    all IDs distinct (sampled without replacement)
    duplicates="allowed": IDs sampled with replacement, so repeats occur
    """
    rng = random.Random(seed)
    if duplicates == "none":
        return [2 * k for k in rng.sample(range(10 * n + 10), n)]
    if duplicates == "allowed":
        return [2 * rng.randrange(n + 1) for _ in range(n)]
    raise ValueError("duplicates must be 'none' or 'allowed'")


def make_queries(ids, q, hit_rate, seed):
    """q queries; round(q * hit_rate) are present in ids, the rest absent.

    The order of present and absent queries is shuffled with the same seed.
    """
    rng = random.Random(seed + 1)
    if q > 0 and hit_rate > 0 and not ids:
        raise ValueError("cannot draw present queries from an empty array")
    n_hit = round(q * hit_rate)
    present = [rng.choice(ids) for _ in range(n_hit)]
    top = 2 * max(ids) + 3 if ids else 101
    absent = [2 * rng.randrange(top // 2 + 1) + 1 for _ in range(q - n_hit)]  # odd
    queries = present + absent
    rng.shuffle(queries)
    return queries
