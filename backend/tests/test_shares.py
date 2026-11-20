"""Run: python -m tests.test_shares  (from backend/)"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.shares import active_share_total, recalculate_shares


@dataclass
class Offer:
    status: str = "active"
    pinned: bool = False
    share: int = 0


def test_equal_split_three() -> None:
    offers = [Offer(), Offer(), Offer()]
    recalculate_shares(offers)
    assert [o.share for o in offers] == [34, 33, 33]
    assert active_share_total(offers) == 100


def test_pin_leaves_remainder_for_unpinned() -> None:
    offers = [Offer(pinned=True, share=40), Offer(), Offer()]
    recalculate_shares(offers)
    assert offers[0].share == 40
    assert offers[1].share + offers[2].share == 60
    assert active_share_total(offers) == 100


def test_all_pinned_tops_up_to_100() -> None:
    offers = [
        Offer(pinned=True, share=20),
        Offer(pinned=True, share=30),
    ]
    recalculate_shares(offers)
    assert active_share_total(offers) == 100
    assert offers[0].share == 20
    assert offers[1].share == 80


def test_removed_zero() -> None:
    offers = [Offer(status="removed", share=50), Offer(), Offer()]
    recalculate_shares(offers)
    assert offers[0].share == 0
    assert active_share_total(offers) == 100


if __name__ == "__main__":
    test_equal_split_three()
    test_pin_leaves_remainder_for_unpinned()
    test_all_pinned_tops_up_to_100()
    test_removed_zero()
    print("ok")
