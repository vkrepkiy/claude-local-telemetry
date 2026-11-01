# Tests

Acceptance exists only as tests, never as prose. A test is a **rule written
down**: one row per rule the contract states, written before the
implementation. Everything else is written only when a defect shows it was
missing. Few, sharp, stable — a test costs money to write and again on every
change it pins.

## How many

- **One row per stated rule, not per function.** The contract's doc
  comments and the owner's frames are the list: each behaviour they state
  gets exactly one row, on the happy path. A module with a long contract has
  many rows; a small feature has a handful. Far beyond that means the rows
  test functions, not rules.
- **No second pass by default.** Edge cases — the malformed input, the slow
  dependency, the boundary value — are added one at a time, when a review,
  a smoke run or a live bug finds the hole, red first per `/vk-regression`.
  A separate edge-case pass is run only when the user asks for it, or for a
  module whose whole job is unhappy input (a parser, a protocol adapter).
- **Tables, not test functions.** `it.each` / `describe.each` (or the
  language's equivalent) over rows of input and expected output; a new case is
  a new row, not new test code. One behaviour per row.
- **No mutation testing** (seeded bugs) unless the user asks.

## What to test

- **Input → output behaviour through the contract.** Call the public
  interface, observe what comes out. Never reach into internals.
- **A safety rule always has a row**, however small the feature: "nothing
  opens without an explicit approve", "nothing is approved by default",
  "the child's name never reaches the model". These are the rows that may
  not be skipped.
- **Not tested:**
  - pure helpers — formatting, parsing a string, merging two records — unless
    the helper *is* a stated rule;
  - permutations of one rule — if two rows would fail for the same reason,
    keep one;
  - pixels, layout, styling, latency, implementation details — the UI's look
    is approved as a design, not asserted in tests;
  - test infrastructure as a product — fakes, mocks and fixtures get at most
    a few end-to-end smoke scenarios; the modules that run on them prove them;
  - presentational UI — no test per prop or per static component. An
    interactive component gets its interaction and accessibility semantics
    (role, name, keyboard, focus); design tokens get pure checks such as
    contrast.
- **Where the money goes instead:** one architect review of the PR
  (`/vk-review`). It finds the rule the rows missed; the fix then lands with
  its red-first row.

## How to write them

- **Scenarios are functions of a factory**, not of an implementation:
  `scenarios(createModule)` lives with the contract, both passes, and each
  module's test calls it with its own factory. Neighbours are replaced by
  fakes passed in as dependencies.
- **Not redundant, not brittle.** If two rows would fail for the same reason,
  keep one.
- **No flakiness, by construction:**
  - never sleep or advance ticks; wait for a positive effect (e.g.
    `vi.waitFor`);
  - prove "nothing happened" with a probe: send the next input and wait for
    *its* effect — this works because the contract processes inputs in order;
  - inject time (`getCurrentTime: () => Date`) instead of faking global
    timers, which also freeze the real implementation's async work.
- **The implementation proves them passable.** No throwaway draft, except for
  a scenario that depends on async work or timing: run it against a
  deliberately slow draft, then delete the draft. A scenario that only passes
  when things are fast is a timing test in disguise.

## Apps

An app (Flutter, Kotlin, …) has requirements too, owned by the human like a
module's scenarios:

- **A pure core layer** holds the behaviour; the UI is a thin shell over it.
- **Requirement tests** live in a protected `…/test/requirements/` folder and
  test the core only. Only test agents write there; implementers never edit
  it.
- **New behaviour starts with its interface:** declare it in the core with a
  doc comment on every member and bodies that only throw
  (`throw UnimplementedError()`), like a TS contract. Then one row per stated
  rule, as for any module.

## When they are wrong

A live bug means a test was wrong or missing. Find the scenario that should
have caught it; fix or delete wrong ones in the same change, saying why; add
an end-to-end regression through the real modules (only the outside world
faked), see it fail on `main`, then fix. This is how edge cases enter the
suite: one at a time, each with a defect behind it.
