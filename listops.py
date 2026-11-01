"""Pure logic for the Merge tab's file list. Items are (name, checked) tuples; nothing here touches Qt."""


def can_move(items, step):
    """True if at least one ticked item has an unticked neighbour in direction `step` (-1 up, +1 down)."""
    return any(items[i][1] and not items[i + step][1]
               for i in range(len(items)) if 0 <= i + step < len(items))


def move_checked(items, step):
    """Move the ticked group one step; it jumps over the unticked neighbour and keeps its internal order."""
    items = list(items)
    n = len(items)
    for i in (range(1, n) if step < 0 else range(n - 2, -1, -1)):
        j = i + step
        if items[i][1] and not items[j][1]:
            items[i], items[j] = items[j], items[i]
    return items


def remove_checked(items):
    return [it for it in items if not it[1]]


def set_all(items, checked):
    return [(name, checked) for name, _ in items]


def toggle(items, index):
    """Flip one item; an out-of-range index changes nothing."""
    items = list(items)
    if 0 <= index < len(items):
        items[index] = (items[index][0], not items[index][1])
    return items


def check_state(items):
    """'none' | 'some' | 'all' (an empty list counts as 'none')."""
    ticked = sum(1 for _, c in items if c)
    return "none" if ticked == 0 else "all" if ticked == len(items) else "some"
