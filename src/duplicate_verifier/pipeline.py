from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from time import perf_counter

from tqdm import tqdm

from duplicate_verifier.constants import DEFAULT_HAMMING_THRESHOLD
from duplicate_verifier.grouping import cluster_hashes
from duplicate_verifier.hashing import hamming_distance, perceptual_fingerprint, sha256_file
from duplicate_verifier.models import AnalysisResult, DuplicateGroup, GroupKind, ImageFile
from duplicate_verifier.quality import pick_keep


def default_workers() -> int:
    cpu = os.cpu_count() or 2
    return max(1, min(8, cpu))


def analyze(
    files: list[ImageFile],
    *,
    threshold: int = DEFAULT_HAMMING_THRESHOLD,
    exact_only: bool = False,
    workers: int | None = None,
    progress: bool = True,
) -> AnalysisResult:
    started = perf_counter()
    worker_count = default_workers() if workers is None else max(1, workers)

    _assign_sha256(files, workers=worker_count, progress=progress)

    by_sha: dict[str, list[ImageFile]] = defaultdict(list)
    failed: list[ImageFile] = []
    for image in files:
        if not image.sha256:
            failed.append(image)
            continue
        by_sha[image.sha256].append(image)

    if exact_only:
        groups = _groups_from_sha_map(by_sha)
        return AnalysisResult(
            groups=_sorted_groups(groups),
            failed=failed,
            unique_contents=len(by_sha),
            elapsed_seconds=perf_counter() - started,
        )

    decode_failed = _assign_perceptual(by_sha, workers=worker_count, progress=progress)
    for image in decode_failed:
        if image not in failed:
            failed.append(image)

    groups = _groups_from_visual_clusters(by_sha, threshold)
    grouped_ids = {id(item) for group in groups for item in group.files}
    failed = [image for image in failed if id(image) not in grouped_ids]

    return AnalysisResult(
        groups=_sorted_groups(groups),
        failed=failed,
        unique_contents=len(by_sha),
        elapsed_seconds=perf_counter() - started,
    )


def _assign_sha256(files: list[ImageFile], *, workers: int, progress: bool) -> None:
    if not files:
        return
    if workers == 1 or len(files) == 1:
        iterator = tqdm(files, desc="SHA-256", unit="arq", disable=not progress)
        for image in iterator:
            digest, error = sha256_file(str(image.path))
            image.sha256 = digest or None
            image.error = error
        return

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(sha256_file, str(image.path)): image for image in files}
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="SHA-256",
            unit="arq",
            disable=not progress,
        ):
            image = futures[future]
            digest, error = future.result()
            image.sha256 = digest or None
            image.error = error


def _assign_perceptual(
    by_sha: dict[str, list[ImageFile]],
    *,
    workers: int,
    progress: bool,
) -> list[ImageFile]:
    """Fingerprint one readable file per unique content; copy metadata to copies."""
    decode_failed: list[ImageFile] = []
    pending: list[tuple[str, ImageFile]] = []
    for digest, copies in by_sha.items():
        representative = max(copies, key=lambda item: item.size_bytes)
        pending.append((digest, representative))

    fingerprints = _fingerprint_many([item.path for _, item in pending], workers, progress)
    by_path = {item["path"]: item for item in fingerprints}

    unresolved: list[tuple[str, list[ImageFile]]] = []
    for digest, representative in pending:
        meta = by_path[str(representative.path)]
        if meta["error"] or meta["phash"] is None:
            unresolved.append((digest, by_sha[digest]))
            continue
        _apply_fingerprint(by_sha[digest], meta)

    for digest, copies in unresolved:
        applied = False
        for candidate in copies:
            meta = perceptual_fingerprint(str(candidate.path))
            if meta["error"] or meta["phash"] is None:
                candidate.error = str(meta["error"] or "falha ao decodificar imagem")
                continue
            _apply_fingerprint(copies, meta)
            applied = True
            break
        if not applied:
            decode_failed.extend(copies)

    return decode_failed


def _fingerprint_many(paths: list, workers: int, progress: bool) -> list[dict[str, object]]:
    str_paths = [str(path) for path in paths]
    if not str_paths:
        return []
    if workers == 1 or len(str_paths) == 1:
        iterator = tqdm(str_paths, desc="pHash", unit="arq", disable=not progress)
        return [perceptual_fingerprint(path) for path in iterator]

    results: list[dict[str, object]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(perceptual_fingerprint, path) for path in str_paths]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="pHash",
            unit="arq",
            disable=not progress,
        ):
            results.append(future.result())
    return results


def _apply_fingerprint(copies: list[ImageFile], meta: dict[str, object]) -> None:
    for image in copies:
        image.phash = int(meta["phash"])  # type: ignore[arg-type]
        image.width = int(meta["width"])  # type: ignore[arg-type]
        image.height = int(meta["height"])  # type: ignore[arg-type]
        image.format = str(meta["format"]) if meta["format"] else None
        image.error = None


def _groups_from_sha_map(by_sha: dict[str, list[ImageFile]]) -> list[DuplicateGroup]:
    groups: list[DuplicateGroup] = []
    for copies in by_sha.values():
        if len(copies) < 2:
            continue
        keep, delete = pick_keep(copies)
        groups.append(DuplicateGroup(kind=GroupKind.EXACT, keep=keep, delete=delete))
    return groups


def _groups_from_visual_clusters(
    by_sha: dict[str, list[ImageFile]],
    threshold: int,
) -> list[DuplicateGroup]:
    indexed: list[tuple[str, int, list[ImageFile]]] = []
    leftover_exact: list[list[ImageFile]] = []

    for digest, copies in by_sha.items():
        phash = copies[0].phash
        if phash is None:
            if len(copies) > 1:
                leftover_exact.append(copies)
            continue
        indexed.append((digest, phash, copies))

    groups: list[DuplicateGroup] = []
    for copies in leftover_exact:
        keep, delete = pick_keep(copies)
        groups.append(DuplicateGroup(kind=GroupKind.EXACT, keep=keep, delete=delete))

    if not indexed:
        return groups

    hashes = [item[1] for item in indexed]
    clusters = cluster_hashes(hashes, threshold)

    for members in clusters:
        files: list[ImageFile] = []
        unique_shas: set[str] = set()
        unique_hashes: list[int] = []
        for index in members:
            digest, phash, copies = indexed[index]
            unique_shas.add(digest)
            unique_hashes.append(phash)
            files.extend(copies)
        if len(files) < 2:
            continue
        keep, delete = pick_keep(files)
        kind = GroupKind.EXACT if len(unique_shas) == 1 else GroupKind.VISUAL
        groups.append(
            DuplicateGroup(
                kind=kind,
                keep=keep,
                delete=delete,
                max_hamming=_max_hamming(unique_hashes),
            )
        )
    return groups


def _max_hamming(hashes: list[int]) -> int:
    unique = list(set(hashes))
    worst = 0
    for i, left in enumerate(unique):
        for right in unique[i + 1 :]:
            worst = max(worst, hamming_distance(left, right))
    return worst


def _sorted_groups(groups: list[DuplicateGroup]) -> list[DuplicateGroup]:
    return sorted(groups, key=lambda group: group.reclaimable_bytes, reverse=True)
