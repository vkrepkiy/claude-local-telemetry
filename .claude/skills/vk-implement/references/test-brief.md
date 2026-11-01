# Test brief (template)

Fill the angle brackets and send this as the spawn prompt. One template for
both passes; the pass decides the lines marked with it.

---

Write the `<happy-path | edge-case>` tests of the module `<module>`. Do not
implement it.

Read first: the repository's `CLAUDE.md` / `AGENTS.md`, then your context
pack `<pack path>` — the contract `<contract paths>`, `testing.md` (what to
test and how), the layout to follow `<example test path>`<; edge cases: the
module `<module path>` and its implementer's report>.

Work on branch `<branch>` from a fresh `<base>`. Write only
`<scenarios path>`. Run `<the module's test command>`:

- happy path: every row fails on the unimplemented body, none on the test
  itself;
- edge cases: commit the green rows together and each red row in its own
  commit `test(<module>): <behaviour>`.

Commit per `/vk-coding-style`, push the branch, do not open a PR. Reply with
exactly these four lines:

```
pushed: yes|no <branch> <commit sha>
rows: <n> in <m> tables
red rows (edge cases): <behaviour — expected vs got, one per line, or "none">
contract leaves open: <list or "none">
```
