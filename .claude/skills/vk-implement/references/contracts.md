# Contracts and boundaries

Anything that crosses a boundary — an HTTP response, an event, a return value
from one module to another — follows these rules. Private helpers and
in-module functions return plain values; no fanaticism.

## Envelope

```ts
interface Envelope<Data, Metadata extends object = {}> {
  data: Data;
  metadata?: Metadata; // pagination, warnings, deprecation notices, trace ids…
}
```

- Collections: `{ data: Item[]; metadata?: { cursor?: string } }`. Never a
  bare array.
- Entities are objects, never bare primitives: `{ id, … }`, not `string`.
  There must always be room for one more field.

## Tolerant reader

- Ignore unknown fields. Never fail on extra keys.
- Every `switch` over a union or enum from a contract has a `default` branch
  that handles "unknown value" (log, skip, or return an error envelope). It
  never throws on a new variant — otherwise a new enum value is a breaking
  change.

## Breaking changes

Breaking = removing a field, renaming it, changing its type or meaning, making
an optional field required, narrowing accepted inputs.

Default: forbidden. Before proposing one, answer in the PR: **why can't this
be additive?**

**Before the first production user** breaking is allowed and cheaper: remove
the old field instead of deprecating, update every consumer in the same wave.
The rule starts to bind with the first production user.

### Extend and deprecate (preferred)

1. Add the new member next to the old one.
2. Mark the old one with JSDoc `@deprecated`, naming the version and the
   replacement:
   ```ts
   /** @deprecated v1.3 — use `displayName`. Remove when unused. */
   name: string;
   ```
3. Keep the old member working; migrate consumers in separate PRs.
4. When lint (`no-deprecated`) or typecheck shows zero usages, a cleanup PR
   removes it.

### New major version (last resort)

- Every API carries a version from day one: HTTP `/v1/…`, TS contracts
  `…/src/v1/…` imported as `…/v1`, events `"task.done/v1"`.
- A breaking change creates `v2` next to `v1`; `v1` stays alive and is
  `@deprecated` as a whole until a scan shows zero usages.
- Versions are integers: `v1`, `v2`, `v12`. Never `v1.1` in a path.

## Other contract defaults

- **Errors are a union of codes.** Each method declares what it can return:
  `Result<Task, "name_taken">`; `"internal"` is always possible. Exceptions
  are for the unexpected only.
- **Time is an ISO UTC string** exactly as `toISOString()` prints it, never a
  `Date`: it survives JSON, databases and the network.
- **Pagination cursors are opaque.** The client never parses one, only hands
  it back.
- **Authentication (who you are) is separate from authorization (what you
  may do).** An authorization result is an object (`Grant`), not `true`, so
  permissions can be added later.
- **A module factory `create<Module>(dependencies)` is part of the contract**,
  so neighbours can be replaced by fakes and the module tested in isolation.
- A contract a human reviews must be readable by a human: JSDoc on every
  member states the behaviour, and every stated behaviour has a test.

## Contract PR checklist

- [ ] boundary payloads use `Envelope`
- [ ] only additive changes, or the PR explains why not and introduces `vN+1`
- [ ] replaced members carry `@deprecated` with version and replacement
- [ ] consumers' `switch`es over changed unions have a `default`
- [ ] functions are verbs, nothing is abbreviated
