"""Private invariants for networks materialized from one ordered sequence."""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Hashable, Mapping


def validate_ordered_transition_counts(
    node_counts: Mapping[Hashable, int],
    edge_counts: Mapping[tuple[Hashable, Hashable], int],
    *,
    object_name: str,
) -> None:
    """Prove that aggregate transitions can come from one ordered sequence.

    Evaluators suppress adjacent self-transitions, so the edge multiset must
    form one directed Euler trail after consecutive equal members are
    compressed.  Node occurrence counts may exceed the compressed trail counts
    because repeated equal members can be restored, but they may not be lower.
    """

    if not edge_counts:
        if len(node_counts) != 1:
            raise ValueError(
                f"{object_name} invariant failed: multiple nodes without transitions cannot form one ordered sequence"
            )
        return

    incoming: dict[Hashable, int] = defaultdict(int)
    outgoing: dict[Hashable, int] = defaultdict(int)
    neighbours: dict[Hashable, set[Hashable]] = defaultdict(set)
    for (left, right), count in edge_counts.items():
        outgoing[left] += count
        incoming[right] += count
        neighbours[left].add(right)
        neighbours[right].add(left)

    participating = set(incoming) | set(outgoing)
    if participating != set(node_counts):
        raise ValueError(
            f"{object_name} invariant failed: isolated nodes cannot occur beside a transition path"
        )

    unseen = set(participating)
    queue = deque((next(iter(unseen)),))
    unseen.remove(queue[0])
    while queue:
        node = queue.popleft()
        for neighbour in neighbours[node]:
            if neighbour in unseen:
                unseen.remove(neighbour)
                queue.append(neighbour)
    if unseen:
        raise ValueError(
            f"{object_name} invariant failed: transitions do not form one connected ordered path"
        )

    starts: list[Hashable] = []
    ends: list[Hashable] = []
    for node in node_counts:
        balance = outgoing[node] - incoming[node]
        if balance == 1:
            starts.append(node)
        elif balance == -1:
            ends.append(node)
        elif balance != 0:
            raise ValueError(
                f"{object_name} invariant failed: transition degrees cannot form one ordered path"
            )

    if len(starts) == len(ends) == 1:
        end = ends[0]
        required = {
            node: outgoing[node] + (1 if node == end else 0)
            for node in node_counts
        }
        if any(node_counts[node] < count for node, count in required.items()):
            raise ValueError(
                f"{object_name} invariant failed: node occurrences cannot supply transition degrees"
            )
        return

    if starts or ends:
        raise ValueError(
            f"{object_name} invariant failed: transition degrees cannot form one ordered path"
        )

    # An Euler circuit becomes a linear sequence by repeating its chosen start
    # at the end.  At least one node must have room for that extra occurrence.
    if not any(
        node_counts[candidate] >= outgoing[candidate] + 1
        and all(
            node_counts[node] >= outgoing[node]
            for node in node_counts
            if node != candidate
        )
        for candidate in node_counts
    ):
        raise ValueError(
            f"{object_name} invariant failed: node occurrences cannot linearize the transition circuit"
        )

