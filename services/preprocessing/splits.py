"""Stratified validation sampling and train/dev/test splits."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any, Iterable, Sequence


def _by_key(rows: Sequence[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[str(row.get(key) or "Unknown")].append(row)
    return buckets


def stratified_sample(
    rows: Sequence[dict[str, Any]],
    n: int,
    *,
    key: str = "Domain",
    seed: int = 42,
    min_per_group: int = 10,
) -> list[dict[str, Any]]:
    """Sample ~n rows proportional to group size, with a floor per group."""
    if n <= 0 or not rows:
        return []
    if n >= len(rows):
        return list(rows)

    rng = random.Random(seed)
    buckets = _by_key(rows, key)
    groups = sorted(buckets.keys())
    total = len(rows)

    # Initial proportional allocation with floor.
    alloc: dict[str, int] = {}
    for g in groups:
        share = len(buckets[g]) / total
        alloc[g] = min(len(buckets[g]), max(min_per_group, int(round(share * n))))

    # Shrink if over-allocated.
    while sum(alloc.values()) > n:
        # Reduce largest groups first, never below 1 if group has rows.
        g = max(groups, key=lambda x: alloc[x])
        if alloc[g] <= 1:
            break
        alloc[g] -= 1

    # Grow if under-allocated.
    while sum(alloc.values()) < n:
        g = max(groups, key=lambda x: len(buckets[x]) - alloc[x])
        if alloc[g] >= len(buckets[g]):
            # All full — stop.
            if all(alloc[x] >= len(buckets[x]) for x in groups):
                break
            continue
        alloc[g] += 1

    sampled: list[dict[str, Any]] = []
    for g in groups:
        pool = list(buckets[g])
        rng.shuffle(pool)
        sampled.extend(pool[: alloc[g]])
    rng.shuffle(sampled)
    return sampled[:n]


def stratified_split(
    rows: Sequence[dict[str, Any]],
    *,
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    key: str = "Domain",
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Split rows into train/dev/test preserving group proportions."""
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError(f"ratios must sum to 1.0, got {ratios}")
    rng = random.Random(seed)
    buckets = _by_key(rows, key)
    train: list[dict[str, Any]] = []
    dev: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []

    for g in sorted(buckets.keys()):
        pool = list(buckets[g])
        rng.shuffle(pool)
        n = len(pool)
        n_train = int(math.floor(n * ratios[0]))
        n_dev = int(math.floor(n * ratios[1]))
        # Remainder goes to test so counts add up.
        n_test = n - n_train - n_dev
        # Ensure tiny groups still get a test/dev row when possible.
        if n >= 3 and n_test == 0:
            n_test = 1
            if n_train > n_dev:
                n_train -= 1
            else:
                n_dev = max(0, n_dev - 1)
        if n >= 2 and n_dev == 0 and n_train > 1:
            n_dev = 1
            n_train -= 1
        train.extend(pool[:n_train])
        dev.extend(pool[n_train : n_train + n_dev])
        test.extend(pool[n_train + n_dev : n_train + n_dev + n_test])

    rng.shuffle(train)
    rng.shuffle(dev)
    rng.shuffle(test)
    return train, dev, test


def pick_validation_from_heldout(
    train: Sequence[dict[str, Any]],
    dev: Sequence[dict[str, Any]],
    test: Sequence[dict[str, Any]],
    n: int = 500,
    *,
    key: str = "Domain",
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Prefer test+dev for native validation; fill from train if needed."""
    preferred = list(test) + list(dev)
    if len(preferred) >= n:
        return stratified_sample(preferred, n, key=key, seed=seed)
    needed = n - len(preferred)
    filler = stratified_sample(train, needed, key=key, seed=seed + 1)
    return list(preferred) + filler


def count_by(rows: Iterable[dict[str, Any]], key: str = "Domain") -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for row in rows:
        out[str(row.get(key) or "Unknown")] += 1
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
