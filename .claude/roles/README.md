# roles

Personas. Each is a lens a subagent wears while writing one note — not an agent
definition, just markdown a subagent is told to read first.

| role | lens |
| --- | --- |
| `critic` | assumptions, failure modes, what to cut |
| `pm` | scope, sequencing, what ships first |
| `architect` | boundaries, coupling, what this makes hard later |
| `marketer` | who it is for, the strongest objection |
| `psychologist` | what people will actually do, where they abandon |
| `producer` | `scope: video` — a rendered short-video candidate: hook, story line, truth to the footage, the phone |

`/vk-consult` builds its menu by listing this directory, so anything dropped
here is immediately selectable. `README.md` is skipped — it documents the
directory, it is not a lens. Every other `.md` here is one.

## Format

First line must be `purpose: <one line>` — that is what the role list prints.
Second line must be `scope: <domain>` (every role here today is
`scope: engineering`; see **Non-engineering roles** below). Then a short lens,
four or five questions worth asking, and one sentence on what a bad note from
this role looks like. Copy `critic.md` for the shape.

Keep them short. Several roles run in parallel and the main thread reads every
note, so a role that writes an essay taxes the whole conversation.

## Why here and not `agents/`

Claude Code auto-discovers `agents/` for subagent definitions, and these are not
that. Two reasons to keep them as plain markdown in a directory of my own:

- `consult` owns its menu. Roles in `agents/` would also surface as standalone
  agents everywhere in the plugin.
- Plain markdown with a `purpose:` line is the one piece of this repo that ports
  to a non-Claude harness unchanged. `agents/` is a Claude-specific format.

The cost is that nothing discovers them automatically — skills read them from
`<plugin root>/roles/`, the root the workspace block prints as `PLUGIN_ROOT:`.

## Non-engineering roles

The lens idea is not specific to code; a `tutor` persona for helping my kid is
the same mechanism. Decided (2026-09-12): a `scope:` field next to `purpose:`,
not a subdirectory — it is one line to add per role, and `consult`'s menu
already reads the file line-by-line rather than the directory structure.

`consult` lists only `scope: engineering` roles by default — the working
scope for a session in a git repo. A role in a different scope (`scope:
parenting`, say) stays out of that menu until something asks for it by name or
by scope explicitly; see [`skills/consult/SKILL.md`](../skills/consult/SKILL.md)
for the exact filter.
