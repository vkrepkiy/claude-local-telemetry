---
name: vk-coding-style
description: Val's defaults for naming, commits, history, pull requests, the backlog and the last message of a turn in any of Val's repositories - verbs for functions, no abbreviations, Conventional Commits, one change per commit, reshape history before main but never after, rebase-merge, when to push and open a PR (cloud vs local mode), fetching before work and keeping every remote in sync, one backlog.md per repository, and the status that ends every turn handed back to the user. Load it before writing code, naming things, committing, rebasing, merging or opening a pull request, before starting work on a branch, before ending a turn, whenever the backlog comes up, and at the start of a session in a repository. Also when the user says "code style", "naming", "commit message", "merge strategy", "add to the backlog", "what's next", "добавь в бэклог", "что дальше", "at the start of a session", "продолжи", "с чего начать".
---

Val's defaults. The repository's own `CLAUDE.md`, `AGENTS.md` and style docs
win wherever they say something; this file only fills the gaps. It covers
names, history and how a turn ends, nothing else — how to design and implement is up to you.

## Naming

- **Functions are verbs:** `createClock`, `listPending`, `handleEvent`,
  `asConversationId` — never nouns like `data()` or `pending()`. Values and
  types are nouns.
- **No abbreviations:** `dependencies` not `deps`, `workingDirectory` not
  `cwd`, `durationMilliseconds` not `durationMs`, `error` not `err`.
  Acronyms that read as words are fine (`id`, `url`, `api`, `json`, `http`),
  and so are one-letter parameters in short, strictly typed lambdas.
- Code, identifiers and commit messages in English.

## Commits

- **Conventional Commits:** `type(scope): summary`, lowercase, imperative, no
  trailing period. Types: `feat fix refactor perf style test docs build ci
  chore revert`. References (issues, tasks) go in trailers, never in the
  subject.
- **One commit = one meaningful change.** No "wip", "fix review" or
  "address comments" commits: fold a fix into the commit it fixes.

  ```bash
  git commit --fixup <sha>
  GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash origin/main
  ```

## History and merging

- **Before `main`, shape the history; after `main`, never touch it.** On
  your branch or in an open PR, fold, reorder and reword with an interactive
  rebase and push with `--force-with-lease` (never `--force`) — always
  allowed on your own branches. Before overwriting a remote branch, fetch
  deep enough and check that the commits you drop are already in `main`, by
  subject (rebase-merge changes the SHAs). A commit on `main` or on someone
  else's branch is undone with `git revert`.
- **Branch names:** when the repository's CI derives the module from the
  branch, a module branch is named exactly `agent/<module>`; a contract
  change for it is `contract/<module>-<what>`. A module's files may live
  outside `packages/<module>` too — an app under `apps/<module>` belongs to
  that module's branch.
- **Rebase-merge only**, no squash, no merge commits. Bring `main` in with
  `git rebase origin/main`.
- **No draft PRs.** A PR that waits on something is opened ready, saying what
  it waits for.
- Run the repository's own checks before every push.
- **A bug fix carries its regression check** in the same commit — a check
  that failed before the fix — per `/vk-regression`.

## Tests

Tests are rules written down, and each costs money twice: when written and
on every change it pins. So:

- **One row per stated rule**, on the happy path, before the implementation —
  the contract's doc comments and the owner's frames are the list. Not one
  per function.
- **Edge cases only behind a defect**: a review, a smoke run or a live bug
  finds the hole, the row goes in red first, then the fix (`/vk-regression`).
  No separate edge-case pass unless the user asks.
- **A safety rule always has a row**, however small the change.
- **Pure helpers get none** — formatting, parsing, merging records — unless
  the helper is itself a stated rule.
- The money saved goes to one architect review per PR (`/vk-review`).

## When to push and open a PR

The environment variable `CLAUDE_CODE_REMOTE=true` means cloud, anything else
local; the user saying "cloud" or "local" wins.

- **cloud** (a Claude Code cloud session): finished work always ends in a
  pushed branch and an open PR, without asking — that is how it gets
  reviewed. The backlog is the exception: it goes straight to the default
  branch (see Backlog).
- **local** (Val's own machine, work repositories included): every local
  branch and commit is pushed, to every remote — nothing lives only on the
  machine (see below). A PR is opened only when Val says the history is
  ready.

## Syncing with remotes

- **Before starting work on any branch**, cloud or local: `git fetch --all
  --prune` and compare the branch with its upstream. Someone else's commits
  are brought in before you write anything — fast-forward, or rebase your
  unpushed commits onto them; never start on a stale branch.
- **Local mode: stay in sync with every remote** (`git remote` lists them).
  A branch or commit that exists locally but not on a remote is pushed —
  after each commit, and again before ending the turn. A new branch is
  pushed with `-u`; a reshaped one with `--force-with-lease`, after the
  check above that the commits it drops are already in `main`.
- Before ending a turn in local mode, `git status -sb` shows no `ahead`
  on any branch you touched; if a push was refused, say so in the status.

## Backlog

One file per repository: `backlog.md` at the root, written in the user's
language (Russian for Val). It is the handoff a fresh session starts from, so
it has one fixed shape:

```
# Backlog

## Now — YYYY-MM-DD
State: <where the work stands>. In flight: <open PRs (links), what each waits for>.
Owner owes: <what the user must do>. Next: <the first action>. Dated: <expiries, reminders>.

## Next
- p1 <outcome, in the user's words> — <link to the source>

## Later
- p3 <recorded, not planned>
```

- **`## Now`** is one handoff, at most ~15 lines (State / In flight / Owner
  owes / Next / Dated). It is replaced at every update, never appended.
- **`## Next`**: one line per item, in the order the work is done — the first
  line is the next task whatever its `p` says. `p1`–`p3` only say how much it
  matters; only the user raises a priority.
- **`## Later`**: recorded, not planned.
- **One line per item.** Detail lives in the linked source (PR, doc, issue).
- **Done items are deleted** in the commit that does the work — git keeps the
  history. What a done item leaves behind (an expiry, a manual step) becomes
  its own line, or goes to `## Now` when dated.
- **The goal is not an item:** why the repository exists and its key
  scenarios live in `GOAL.md`, the owner's (`/vk-compass`); the backlog
  holds work.
- **Decisions, spike results, lessons and history are not items.** They go to
  the repository's decision record (its ADRs or docs; otherwise create
  `docs/decisions.md`), and options the owner rejected to `docs/rejected.md`
  with the owner's words. Items link them.
- **Another repository's work** is one line pointing at that repository's
  backlog, never its state.
- **The backlog loses to code and docs.** A line that is done, contradicted or
  overtaken is fixed in the turn that notices it.
- A backlog in another shape is migrated once, keeping its language and
  wording.

**The backlog needs no owner.** It is the handoff between sessions, not a
decision: what the owner approved or asked for in chat, and the state a turn
leaves behind, is written without asking and without a review. Edit the file
directly — no tracker, no issues, no PR. Commit it alone as
`chore(backlog): <what changed>` on the default branch (fetch and rebase onto
it first) and push, in cloud and local mode alike. Never put it into a work
PR — the handoff would wait for a merge and conflict with every other branch.
If the push to the default branch is refused, say so once in the status;
don't open a PR for it. Something real but out of scope found while working is added to
`## Later` as `p3`. Asked "what's next", read `## Now` and `## Next` and answer
with the first lines.

### Recommend, don't dictate

Items, `## Now` and the new-session prompt set three things:

- the **goal** — the outcome in the user's words, and why now;
- the **constraints** — owner decisions and limits (budget, data rules, what
  was rejected), each with its source;
- the **acceptance** — checkable by someone who was not there.

They never say which file, function, model, library or endpoint to use, or the
steps — unless that choice is itself an owner decision; then it is a
constraint with its source. What exists may be pointed at as a fact, through
the document that describes it, marked optional: "Known: X exists (doc);
reuse or replace". Contracts, scenarios, decision records and
`docs/rejected.md` are binding boundaries. Paths to secrets, hosts and
commands belong in a runbook, not an item.

Test: if a session that reached the goal inside the constraints by another
route would have "failed" the item, the item dictates.

- Good: "next we choose an agent for X and implement it under conditions Y".
- Bad: "change file Z"; "wire Haiku 3.5 into S".

## Handing the turn back

Whenever the lead session stops and returns the turn to the user, the **last
thing in its message** is a status of at most 4 sentences, in the user's
language, in one of three states:

- **nothing needed** — and what wakes the session: an agent finishing, a
  GitHub event, a check-in at a stated time;
- **an action** — the exact action, a link for every PR or artifact it needs,
  and how the session learns it is done: "tell me" or "I get notified
  automatically";
- **a question** — the question and the default taken if unanswered.

When the turn landed product work, the status also says what the user can
click or try now — a preview link, the command for a local preview, a demo on
mocks — or plainly that nothing is touchable yet and after which step it will
be.

No other summary in the message repeats it. Examples:

- "Агенты запущены в фоне, я вернусь, когда они завершат выполнение, ничего не требуется."
- "Открыто 4 PR (ссылки), поставь тег X, сообщи, когда сделаешь."
- "Прочитай PR, сделай мердж, я автоматически получу уведомление и продолжу."

## Session hygiene

A session is not a place to live. The handoff lives in `backlog.md`, and the
user never has to ask "with what prompt?". Three rules; the first is the
reader's, the others are checked at every hand-back, before the status:

- **Start from the backlog.** A session's first act in a repository is to read
  `GOAL.md` (if any), then `CLAUDE.md` / `AGENTS.md`, then `backlog.md` →
  `## Now`; a repository without `GOAL.md` gets `/vk-compass`'s offer to
  write one. If `## Now` is older than later commits, or disagrees with the
  open PRs or the code, say so in one line and reconcile the backlog before
  other work. If neither `CLAUDE.md` nor `AGENTS.md` names `backlog.md`,
  propose the line "Start from `backlog.md` → `## Now`." New work the user asks for outside the backlog
  gets a `/vk-compass` verdict before it starts.
- **Write the handoff before the context is the problem.** At the end of
  every turn that merged, opened or finished something, `## Now` is replaced
  (not appended) with the current state, and every line of `## Next` that the
  turn made done or stale is deleted or rewritten. It is pushed straight to
  the default branch (`chore(backlog): …`, see Backlog), not into the work's
  PR, and kept current even when no new session is proposed.
- **Say when to switch, and give the prompt.** Add one highlighted line to
  the status in exactly these cases, never from a feeling about size:
  - **`🔀 New session`** — a milestone is done (its PRs merged or only
    waiting on the user, the handoff written), or the next step belongs
    to another repository or another kind of work (deploy and live runs
    after design, one module after a split).
  - **`🗜️ Compact`** — mid-milestone, with branches or agents in flight,
    after a turn that spent most of its output on tool results, logs or
    agent reports the next step will not need.

  The `🔀` line is always followed by the prompt for the new session, in a
  fenced block, ready to paste. The prompt only points: the repository (and
  the branch if not `main`), "start from `CLAUDE.md` and `backlog.md` →
  `## Now`", and only what the repository cannot hold — a reminder scheduled
  in this session, another repository the next step touches. If the next
  session would need more, fix `## Now`, not the prompt. The prompt follows
  "Recommend, don't dictate". Without the block the line is not allowed.

A session that goes on past these points is the user's choice; the handoff
in `backlog.md` is what makes the choice safe either way.
