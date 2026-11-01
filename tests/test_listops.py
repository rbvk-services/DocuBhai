import itertools
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import listops  # noqa: E402


def L(spec):
    """'A B* C' -> [('A', False), ('B', True), ('C', False)]  (* marks a ticked item)."""
    return [(t.rstrip("*"), t.endswith("*")) for t in spec.split()]


def S(items):
    return " ".join(n + ("*" if c else "") for n, c in items)


@pytest.mark.parametrize("before,step,after", [
    ("A B* C", -1, "B* A C"),             # single ticked item moves up
    ("A B* C", 1, "A C B*"),              # ... and down
    ("A B* C* D", -1, "B* C* A D"),       # a contiguous group jumps over the neighbour, order kept
    ("A B* C* D", 1, "A D B* C*"),
    ("A B* C D*", -1, "B* A D* C"),       # a split group: each ticked item moves one step
    ("A* B C*", -1, "A* C* B"),           # the item already at the top stays; the other still moves
    ("A B C*", 1, "A B C*"),              # at the bottom: nothing happens
    ("A* B C", -1, "A* B C"),             # at the top: nothing happens
    ("A* B* C*", -1, "A* B* C*"),         # everything ticked: nothing to jump over
    ("A B C", 1, "A B C"),                # nothing ticked
    ("A*", -1, "A*"),                     # single-item list
    ("", 1, ""),                          # empty list
])
def test_move_checked(before, step, after):
    assert S(listops.move_checked(L(before), step)) == after


def test_move_does_not_mutate_input():
    items = L("A B* C")
    before = list(items)
    listops.move_checked(items, -1)
    assert items == before


@pytest.mark.parametrize("step", [-1, 1])
def test_can_move_agrees_with_move_for_every_tick_pattern(step):
    """Exhaustive check on 1..5 items: can_move is true exactly when a move changes something, and a move never
    loses, duplicates or re-orders items, never changes who is ticked, and keeps the ticked files' relative order."""
    for n in range(0, 6):
        names = list("ABCDE"[:n])
        for ticks in itertools.product([False, True], repeat=n):
            items = list(zip(names, ticks))
            moved = listops.move_checked(items, step)
            assert listops.can_move(items, step) == (moved != items), (items, step)
            assert sorted(moved) == sorted(items)
            ticked = [x for x in items if x[1]]
            assert [x for x in moved if x[1]] == ticked  # same ticked files, same relative order


def test_moving_repeatedly_reaches_the_edge_and_stops():
    items = L("A B C D*")
    for _ in range(10):
        items = listops.move_checked(items, -1)
    assert S(items) == "D* A B C"
    assert not listops.can_move(items, -1) and listops.can_move(items, 1)


def test_duplicate_names_are_independent_items():
    items = L("a a* a")
    assert S(listops.move_checked(items, -1)) == "a* a a"
    assert S(listops.toggle(items, 0)) == "a* a* a"


def test_remove_checked():
    assert S(listops.remove_checked(L("A B* C D*"))) == "A C"
    assert listops.remove_checked(L("A* B*")) == []
    assert S(listops.remove_checked(L("A B"))) == "A B"
    assert listops.remove_checked([]) == []


def test_set_all():
    assert S(listops.set_all(L("A B* C"), True)) == "A* B* C*"
    assert S(listops.set_all(L("A B* C"), False)) == "A B C"
    assert listops.set_all([], True) == []


@pytest.mark.parametrize("index", [-1, 3, 99])
def test_toggle_out_of_range_changes_nothing(index):
    assert listops.toggle(L("A B* C"), index) == L("A B* C")


def test_toggle_flips_both_ways():
    assert S(listops.toggle(L("A B* C"), 1)) == "A B C"
    assert S(listops.toggle(L("A B* C"), 0)) == "A* B* C"


@pytest.mark.parametrize("spec,state", [("", "none"), ("A B", "none"), ("A* B", "some"), ("A* B*", "all"), ("A*", "all")])
def test_check_state(spec, state):
    assert listops.check_state(L(spec)) == state
