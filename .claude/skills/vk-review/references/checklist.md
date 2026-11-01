# Acceptance checklist

Work through what applies to the PR's class. Each item is a question with a
yes or no answer; a **no** that would hurt after merging is a finding. A no
that would not hurt is not.

A boundary PR gets every section. An implementation PR gets the security
baseline, the mergeability and label checks, and only the real problems from
the rest: a scenario or contract bypassed, a test weakened or skipped, a
bug fix without a check that failed before it (or a reason it cannot have
one), a silent failure. A deleted test is weakening only while the behaviour
it guarded still exists; one whose behaviour is gone should go
(`/vk-regression`, "When a regression check goes"). If it works acceptably and its tests prove it, accept.

## Security baseline — every PR

- **Secrets never leak:** not into logs, not into argv (visible in `ps`), not
  into the environment handed to a subprocess or SDK that does not need them,
  not into a CI job that runs the PR's code in the same job as a secret.
- **Nothing a less-trusted party can write is executed by a more-trusted
  one:** hooks or config in a git directory shared between users or agents,
  a persistent self-hosted runner that runs PR code, a script fetched from a
  branch or a fork and run with the owner's credentials.
- **Approval labels count only from the accounts allowed to set them**, and
  the gate that reads them checks who set them, not just that they are there.

## Seams — a split's contract PR (`contract/<node>-split`)

Read the shared contract against the requirements the node answers to.

- **Handled.** Every event has a handler; none is emitted for nobody.
- **Exit.** Every state has a way out.
- **One enforcer.** No rule is enforced by two modules.
- **Axis.** No child breaks the axis of the split.

## Business scenarios

- The scenario the PR exists for works: there is a test of its happy path,
  and it would fail if the feature were missing.
- **Boundary PR:** a happy-path row for each public entry of the contract,
  within the budget of `/vk-implement`'s `references/testing.md` and nothing
  from its "Not tested" list. Corner cases are not asked for here; they come
  after the implementation.
- **Implementation PR:** the corner cases that can realistically happen here
  are tested: empty input, the dependency failing, the second call, the
  boundary value. Name the one that is missing; do not ask for exhaustive
  coverage. Not every documented behaviour needs its own test. An edge-case
  row changed to make it pass is a test weakened.

## Readable by a junior

- Each `unclear` snippet from the reader: is it unclear because the code is
  (finding), or because the snippet lacked context a reader of the file has
  (not a finding)?
- A paraphrase that contradicts the code's purpose is a finding: the name or
  the shape is misleading.

## Architecture

- **Isolation.** The module reaches others only through their contracts. No
  new edge from a stable module to a volatile one.
- **State.** After any failure on the path — a dependency down, a half-done
  write, a restart — the system is left in a state it can continue from. Name
  the step that would leave it inconsistent.
- **Extensible.** The next likely requirement fits without rewriting this one.
- **Secure.** Secrets never read, logged or returned. Input validated where it
  enters the system. Access checked where it is granted. (And the baseline
  above.)

## Contracts

- **No silent break.** A removed or renamed member, a narrowed type, or a new
  required field is a breaking change. It is either announced as such (with
  the consumers it breaks) or it is a finding.
- **Room to grow.** Data sits in an envelope or a named object, not in
  positional or top-level fields: `{ data: { … }, metadata }` lets a sibling
  be added later; a bare array or a long parameter list does not. Related
  fields are grouped into one object.
- **Closed sets stay tolerable.** A union or enum a consumer switches over has
  a documented default for unknown values.
- **Behaviour is written down.** Every member says what it does, what it
  returns on failure and when. An implementer should never have to guess.

## Errors and observability

The most important section. An on-call agent will read these errors and try
to fix them without a person; it can only fix what it can see.

- Every failure path ends in an explicit, classified error. Nothing is
  swallowed, nothing becomes `undefined` or a silent default.
- The error carries its cause: which call, which status, the provider's own
  reason, how long it took. Never the secret, never the user's content.
- It reaches the journal or log at the right level, once, where an operator
  looks. A failure that only reaches the user is invisible to on-call.
- The user still hears or sees an outcome. Silence is a failure.
- A path that was observable before this PR is still observable after it.

## External effects

- An external adapter carries evidence of a live run (smoke output) for the
  behaviour it changes. Without it, `changes`.
- Anything that changes how often, how much or how fast we call a paid or
  rate-limited service — retries, splitting, polling, concurrency — names the
  new volume and why the provider will accept it.

## Not findings

Naming and formatting the linter accepts. A different design of equal merit.
Missing tests for unlikely cases. Comments. Performance without a measured or
obvious problem. Anything you would phrase as "consider".
