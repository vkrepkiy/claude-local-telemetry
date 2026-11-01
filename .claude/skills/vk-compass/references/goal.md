# GOAL.md

The owner's file at the repository root, written the way a person explains
the repository to a newcomer: what it is for, then what is in it and why,
then what must keep working and what is never done. At most 40 lines, these
four sections in this order, in the owner's language — the one the
repository's README and backlog use. In English the headings are Why this
repository · Key scenarios · What we don't do · Now.

```
# Зачем этот репозиторий

<First sentence: which system the repository belongs to and what it serves
there, with a link to the system's design where that lives (one repository
of the system holds it; the others link). Then what the repository holds,
one line per part, each with its purpose: "События — журнал жизни: что
ребёнок смотрел…". Never a description of a process or of who does what
day to day — that is the scenarios' job.>

<A part with a goal of its own — an agent role, an app, a service — gets
one line here and its own GOAL.md in its folder, in this same shape with
`## Сейчас` pointing at the root backlog; the compass judges work on that
part against the nested file first. What is planned and not started is
one line, named as such.>

## Ключевые сценарии
- <3–5 lines, each "who does what → what happens"; the compass quotes them>

## Чего не делаем
- <explicit non-goals, one per line, each with its source in parentheses
  where one exists; an `against` verdict cites them>

## Сейчас
[backlog.md → ## Now](backlog.md)
```

`Сейчас` is that one link and nothing else: the state lives in the backlog,
decisions in the decision record, never here.
