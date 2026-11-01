# Research brief (template)

Fill the angle brackets and send this as the spawn prompt.

---

Research the module `<child>` of `<node>` — a `<deployable | package | infra |
capability | unit>` at `<path in the repository>`. Do not design its
insides and do not write code.

Read first: the repository's `CLAUDE.md` / `AGENTS.md`, your context pack
`<pack path>` (excerpts, with `path:line`, of the routes and types, the
requirements and the designs this child touches), and the split:

<children, arrows, owned data, landing order — as approved>

Open a primary source — the requirements `<paths, sections>`, the parent
contract `<path or "none yet">`, the designs — only to check one specific
point the pack leaves open.

Find out, grounding every line in the pack or in something you opened:

- what `<child>` receives and from whom, what it returns or emits and to whom
- the data it owns, and the data it only reads
- every requirement that lands on it, cited by section
- what it needs from each neighbour that the split does not yet give
- a draft of its public contract: types and one doc-comment line per member
- whether the stack hint `<hint, or "none">` holds against the requirements,
  and what in them would break it
- what is undecided and who should decide it

Write the note to `<note path>`, in at most 60 lines, in these sections:
**Interface**, **Owns**, **Requirements**, **Needs from neighbours**,
**Stack**, **Draft contract**, **Open questions**.
