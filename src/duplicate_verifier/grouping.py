from __future__ import annotations

from collections import defaultdict

from duplicate_verifier.hashing import hamming_distance


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, index: int) -> int:
        parent = self.parent
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(self, left: int, right: int) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            self.parent[root_left] = root_right
        elif self.rank[root_left] > self.rank[root_right]:
            self.parent[root_right] = root_left
        else:
            self.parent[root_right] = root_left
            self.rank[root_left] += 1

    def groups(self) -> dict[int, list[int]]:
        clustered: dict[int, list[int]] = defaultdict(list)
        for index in range(len(self.parent)):
            clustered[self.find(index)].append(index)
        return clustered


def _band_parts(value: int, n_bits: int, n_bands: int) -> tuple[int, ...]:
    base = n_bits // n_bands
    extra = n_bits % n_bands
    parts: list[int] = []
    shift = 0
    for band in range(n_bands):
        size = base + (1 if band < extra else 0)
        mask = (1 << size) - 1
        parts.append((value >> shift) & mask)
        shift += size
    return tuple(parts)


def cluster_hashes(hashes: list[int], threshold: int, n_bits: int = 64) -> list[list[int]]:
    """Group similar 64-bit hashes by Hamming distance <= ``threshold``.

    Candidate pairs are generated with banded indexing (pigeonhole principle):
    with ``threshold + 1`` bands, at least one band must match exactly.
    """
    n = len(hashes)
    if n == 0:
        return []
    if n == 1:
        return [[0]]

    uf = UnionFind(n)
    bands = max(threshold + 1, 1)
    buckets: list[dict[int, list[int]]] = [defaultdict(list) for _ in range(bands)]

    for index, value in enumerate(hashes):
        for band, part in enumerate(_band_parts(value, n_bits, bands)):
            buckets[band][part].append(index)

    seen_pairs: set[tuple[int, int]] = set()
    for band_map in buckets:
        for indexes in band_map.values():
            if len(indexes) < 2:
                continue
            for i, left in enumerate(indexes):
                for right in indexes[i + 1 :]:
                    pair = (left, right) if left < right else (right, left)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    if hamming_distance(hashes[left], hashes[right]) <= threshold:
                        uf.union(left, right)

    return [sorted(members) for members in uf.groups().values()]
