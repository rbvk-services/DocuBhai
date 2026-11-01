// Pure logic for the Merge tab's file list (mirror of listops.py). Items are objects with a boolean `checked`;
// every function returns a new array and never touches the DOM.

export const isPdf = (file) => /\.pdf$/i.test(file?.name ?? "") || file?.type === "application/pdf";

/** True if some ticked item has an unticked neighbour in direction `step` (-1 up, +1 down). */
export const canMove = (items, step) =>
  items.some((it, i) => it.checked && items[i + step] !== undefined && !items[i + step].checked);

/** Move the ticked group one step: it jumps over the unticked neighbour and keeps its internal order. */
export function moveChecked(items, step) {
  const out = [...items], n = out.length;
  for (let k = 0; k < n - 1; k++) {
    const i = step < 0 ? k + 1 : n - 2 - k, j = i + step;
    if (out[i].checked && !out[j].checked) [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export const removeChecked = (items) => items.filter((it) => !it.checked);

export const setAll = (items, checked) => items.map((it) => ({ ...it, checked }));

/** Flip one item; an out-of-range or non-integer index changes nothing. */
export function toggle(items, index) {
  if (!Number.isInteger(index) || index < 0 || index >= items.length) return [...items];
  return items.map((it, i) => (i === index ? { ...it, checked: !it.checked } : it));
}

/** 'none' | 'some' | 'all' (an empty list counts as 'none'). */
export function checkState(items) {
  const n = items.filter((it) => it.checked).length;
  return n === 0 ? "none" : n === items.length ? "all" : "some";
}

/** Drag-and-drop: move the item at `from` so it ends up at index `to`. Bad indexes change nothing. */
export function reorder(items, from, to) {
  const ok = (i) => Number.isInteger(i) && i >= 0 && i < items.length;
  if (!ok(from) || !ok(to) || from === to) return [...items];
  const out = [...items];
  out.splice(to, 0, ...out.splice(from, 1));
  return out;
}

export const summary = (items) => `${items.filter((it) => it.checked).length} of ${items.length} selected`;
