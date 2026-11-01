import assert from "node:assert/strict";
import { test } from "node:test";
import * as ml from "../../web/js/mergelist.js";

/** 'A B* C' -> [{name:'A',checked:false}, {name:'B',checked:true}, ...]  (* marks a ticked item) */
const L = (spec) => (spec ? spec.split(" ").map((t) => ({ name: t.replace("*", ""), checked: t.endsWith("*") })) : []);
const S = (items) => items.map((it) => it.name + (it.checked ? "*" : "")).join(" ");

const MOVES = [
  ["A B* C", -1, "B* A C"], // single ticked item moves up
  ["A B* C", 1, "A C B*"], // ... and down
  ["A B* C* D", -1, "B* C* A D"], // a contiguous group jumps over the neighbour, order kept
  ["A B* C* D", 1, "A D B* C*"],
  ["A B* C D*", -1, "B* A D* C"], // a split group: each ticked item moves one step
  ["A* B C*", -1, "A* C* B"], // the item already at the top stays; the other still moves
  ["A B C*", 1, "A B C*"], // at the bottom: nothing happens
  ["A* B C", -1, "A* B C"], // at the top: nothing happens
  ["A* B* C*", -1, "A* B* C*"], // everything ticked: nothing to jump over
  ["A B C", 1, "A B C"], // nothing ticked
  ["A*", -1, "A*"], // single-item list
  ["", 1, ""], // empty list
];
for (const [before, step, after] of MOVES)
  test(`moveChecked '${before}' by ${step} -> '${after}'`, () => assert.equal(S(ml.moveChecked(L(before), step)), after));

test("moveChecked does not mutate its input", () => {
  const items = L("A B* C"), copy = structuredClone(items);
  ml.moveChecked(items, -1);
  assert.deepEqual(items, copy);
});

for (const step of [-1, 1])
  test(`canMove agrees with moveChecked for every tick pattern (step ${step})`, () => {
    for (let n = 0; n <= 5; n++)
      for (let mask = 0; mask < 1 << n; mask++) {
        const items = Array.from({ length: n }, (_, i) => ({ name: "ABCDE"[i], checked: !!(mask >> i & 1) }));
        const moved = ml.moveChecked(items, step);
        assert.equal(ml.canMove(items, step), S(moved) !== S(items), S(items));
        assert.deepEqual(moved.map((x) => x.name).sort(), items.map((x) => x.name).sort()); // nothing lost or duplicated
        assert.equal(moved.filter((x) => x.checked).length, items.filter((x) => x.checked).length);
        // the ticked files keep their relative order
        assert.deepEqual(moved.filter((x) => x.checked).map((x) => x.name), items.filter((x) => x.checked).map((x) => x.name));
      }
  });

test("moving repeatedly reaches the edge and stops", () => {
  let items = L("A B C D*");
  for (let i = 0; i < 10; i++) items = ml.moveChecked(items, -1);
  assert.equal(S(items), "D* A B C");
  assert.ok(!ml.canMove(items, -1) && ml.canMove(items, 1));
});

test("items with the same name are independent", () => {
  assert.equal(S(ml.moveChecked(L("a a* a"), -1)), "a* a a");
  assert.equal(S(ml.toggle(L("a a* a"), 0)), "a* a* a");
});

test("removeChecked / setAll", () => {
  assert.equal(S(ml.removeChecked(L("A B* C D*"))), "A C");
  assert.deepEqual(ml.removeChecked(L("A* B*")), []);
  assert.equal(S(ml.removeChecked(L("A B"))), "A B");
  assert.deepEqual(ml.removeChecked([]), []);
  assert.equal(S(ml.setAll(L("A B* C"), true)), "A* B* C*");
  assert.equal(S(ml.setAll(L("A B* C"), false)), "A B C");
  assert.deepEqual(ml.setAll([], true), []);
});

test("setAll keeps other fields on each item", () => {
  assert.deepEqual(ml.setAll([{ name: "x", file: 7, checked: false }], true), [{ name: "x", file: 7, checked: true }]);
});

for (const bad of [-1, 3, 99, 1.5, NaN, undefined, null, "1"])
  test(`toggle ignores bad index ${String(bad)}`, () => assert.deepEqual(ml.toggle(L("A B* C"), bad), L("A B* C")));

test("toggle flips both ways", () => {
  assert.equal(S(ml.toggle(L("A B* C"), 1)), "A B C");
  assert.equal(S(ml.toggle(L("A B* C"), 0)), "A* B* C");
});

for (const [spec, state] of [["", "none"], ["A B", "none"], ["A* B", "some"], ["A* B*", "all"], ["A*", "all"]])
  test(`checkState '${spec}' is ${state}`, () => assert.equal(ml.checkState(L(spec)), state));

test("reorder (drag and drop) moves one item to a new index", () => {
  assert.equal(S(ml.reorder(L("A B C D"), 0, 2)), "B C A D");
  assert.equal(S(ml.reorder(L("A B C D"), 3, 0)), "D A B C");
  assert.equal(S(ml.reorder(L("A* B C"), 0, 2)), "B C A*"); // ticks travel with their item
});

test("reorder ignores same-position and bad indexes", () => {
  const items = L("A B C");
  for (const [from, to] of [[1, 1], [-1, 0], [0, 3], [5, 1], [0.5, 1], [undefined, 0], [0, null]])
    assert.deepEqual(ml.reorder(items, from, to), items, `${from} -> ${to}`);
});

test("summary text", () => {
  assert.equal(ml.summary([]), "0 of 0 selected");
  assert.equal(ml.summary(L("A B* C*")), "2 of 3 selected");
});

test("isPdf accepts by extension or MIME type and rejects everything else", () => {
  assert.ok(ml.isPdf({ name: "a.pdf" }) && ml.isPdf({ name: "A.PDF" }) && ml.isPdf({ name: "scan", type: "application/pdf" }));
  assert.ok(!ml.isPdf({ name: "a.pdf.exe" }) && !ml.isPdf({ name: "notes.txt", type: "text/plain" }));
  assert.ok(!ml.isPdf({ name: "" }) && !ml.isPdf({}) && !ml.isPdf(null) && !ml.isPdf(undefined));
});
