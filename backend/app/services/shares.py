from __future__ import annotations

from typing import Iterable, List, Protocol


class Shareable(Protocol):
    status: str
    pinned: bool
    share: int


def active_share_total(offers: Iterable[Shareable]) -> int:
    return sum(max(0, o.share) for o in offers if o.status == "active")


def recalculate_shares(offers: Iterable[Shareable]) -> None:
    """Equal-share among active unpinned offers; pinned keep share; removed -> 0.

    Active shares always sum to 100 when there is at least one active offer:
    - unpinned offers split the remainder after pinned
    - if everything is pinned and under 100, leftover goes to the last pinned offer
    - if pinned exceed 100, pinned values are scaled down proportionally
    """
    items: List[Shareable] = list(offers)
    for offer in items:
        if offer.status == "removed":
            offer.share = 0
            offer.pinned = False

    active = [o for o in items if o.status == "active"]
    if not active:
        return

    pinned = [o for o in active if o.pinned]
    unpinned = [o for o in active if not o.pinned]

    pinned_total = sum(max(0, o.share) for o in pinned)
    if pinned_total > 100:
        allocated = 0
        for i, offer in enumerate(pinned):
            if i == len(pinned) - 1:
                offer.share = max(0, 100 - allocated)
            else:
                offer.share = int(round(offer.share * 100 / pinned_total))
                allocated += offer.share
        pinned_total = sum(o.share for o in pinned)

    remaining = max(0, 100 - pinned_total)

    if unpinned:
        base = remaining // len(unpinned)
        leftover = remaining % len(unpinned)
        for index, offer in enumerate(unpinned):
            offer.share = base + (1 if index < leftover else 0)
        return

    # All active offers are pinned: top up the last one so the stream sums to 100.
    if remaining > 0 and pinned:
        pinned[-1].share += remaining
