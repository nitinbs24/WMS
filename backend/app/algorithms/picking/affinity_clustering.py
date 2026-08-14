"""
Apriori-Based Affinity Clustering SKU→Slot Assignment
------------------------------------------------------
Picking Efficiency algorithm #2 (TRD §7, Algorithm Report §4.2).

Affinity principle: SKUs that are frequently ordered together (high
co-occurrence in order lines) should be placed in adjacent or nearby
slots to minimise the travel distance when picking a multi-SKU order.

Algorithm:
1. Build a co-occurrence matrix from order_lines data.
   co_occurrence[a][b] = number of orders containing both SKU a and SKU b.
2. Cluster SKUs using a greedy agglomerative approach:
   - Start each SKU in its own cluster.
   - Merge the two clusters with the highest total affinity score
     until no merge improves total affinity, or we reach target
     cluster_count (= ceil(len(skus) / slots_per_cluster)).
3. Assign each cluster to a contiguous run of slots (sorted by pos_x/pos_y).
   Within a cluster, rank SKUs by pick frequency → best slot first.
4. Unplaceable SKUs → AlgorithmException.

Score = affinity_score × normalised_frequency.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict

from app.algorithms.types import (
    AlgorithmException,
    Assignment,
    OrderLines,
    PickHistory,
    SKU,
    Slot,
    SlotAssignmentResult,
    Thresholds,
)

_SLOTS_PER_CLUSTER = 4   # target slots per affinity cluster


def assign(
    skus: list[SKU],
    slots: list[Slot],
    order_lines: OrderLines,
    thresholds: Thresholds = None,
) -> SlotAssignmentResult:
    """
    Assign SKUs to slots using Apriori affinity clustering.
    """
    if thresholds is None:
        thresholds = Thresholds()
    if not skus or not slots:
        return SlotAssignmentResult(assignments=[], exceptions=[])

    available = [s for s in slots if s.status == "empty"]

    # 1. Build co-occurrence matrix
    co: dict[uuid.UUID, dict[uuid.UUID, float]] = defaultdict(lambda: defaultdict(float))
    for order in order_lines.orders:
        for i, a in enumerate(order):
            for b in order[i + 1:]:
                co[a][b] += 1.0
                co[b][a] += 1.0

    # 2. Greedy affinity clustering
    sku_ids = [s.id for s in skus]
    clusters: list[list[uuid.UUID]] = [[sid] for sid in sku_ids]
    target = max(1, math.ceil(len(skus) / _SLOTS_PER_CLUSTER))

    while len(clusters) > target:
        best_score = -1.0
        best_i, best_j = 0, 1
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                score = _cluster_affinity(clusters[i], clusters[j], co)
                if score > best_score:
                    best_score = score
                    best_i, best_j = i, j
        if best_score <= 0:
            break
        merged = clusters[best_i] + clusters[best_j]
        clusters = [c for idx, c in enumerate(clusters) if idx not in (best_i, best_j)]
        clusters.append(merged)

    # 3. Build SKU lookup
    sku_map = {s.id: s for s in skus}

    # Sort slots by position (aisle traversal order: by pos_y then pos_x)
    sorted_slots = sorted(available, key=lambda s: (s.pos_y, s.pos_x, s.level))

    # Assign clusters to contiguous slot blocks
    assignments: list[Assignment] = []
    exceptions: list[AlgorithmException] = []
    slot_idx = 0

    # Sort clusters by total frequency (busiest clusters get first/best slots)
    def cluster_freq(cluster: list[uuid.UUID]) -> float:
        return sum(sku_map[sid].pick_frequency for sid in cluster if sid in sku_map)

    clusters.sort(key=cluster_freq, reverse=True)

    for cluster in clusters:
        # Within cluster, sort by pick frequency
        cluster.sort(key=lambda sid: sku_map[sid].pick_frequency if sid in sku_map else 0, reverse=True)
        for sku_id in cluster:
            if sku_id not in sku_map:
                continue
            sku = sku_map[sku_id]

            placed = False
            while slot_idx < len(sorted_slots):
                slot = sorted_slots[slot_idx]
                slot_idx += 1
                if slot.weight_capacity >= sku.weight:
                    aff_score = sum(co[sku_id].values()) / max(len(co[sku_id]), 1)
                    max_freq = max((s.pick_frequency for s in skus), default=1.0)
                    norm_freq = sku.pick_frequency / max_freq if max_freq > 0 else 0.0
                    score = round(min(1.0, aff_score / 10) * 0.5 + norm_freq * 0.5, 4)
                    assignments.append(
                        Assignment(pallet_id=None, product_id=sku.id, slot_id=slot.id, score=score)
                    )
                    placed = True
                    break

            if not placed:
                exceptions.append(
                    AlgorithmException(
                        pallet_id=None,
                        product_id=sku.id,
                        reason_code="NO_CLEARANCE_MATCH",
                        reason_detail=f"No eligible slot for SKU {sku.sku} (affinity cluster exhausted slots)",
                    )
                )

    return SlotAssignmentResult(assignments=assignments, exceptions=exceptions)


def _cluster_affinity(a: list[uuid.UUID], b: list[uuid.UUID], co: dict) -> float:
    """Total co-occurrence score between two clusters."""
    total = 0.0
    for x in a:
        for y in b:
            total += co[x].get(y, 0.0)
    return total
