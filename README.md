# claude-local-telemetry

`/usage` shows the total.

&nbsp; &nbsp; OpenTelemetry shows logs.

&nbsp; &nbsp; &nbsp; &nbsp; This utility helps you understand **what AI actually did**.

A local OpenTelemetry Collector saves Claude Code telemetry as JSONL. `analyze.py` turns it into a human-readable report.

## Quick Start

```bash
git clone git@gitlab.com:bestsecret/sandbox/claude-local-telemetry.git ~/claude-otel
cd ~/claude-otel
docker compose up -d
```

From the repository you want to measure:

```bash
source ~/claude-otel/env.sh && claude
```

Use Claude normally, exit, then run:

```bash
python3 ~/claude-otel/analyze.py
```

### Output Example

| # | Prompt             | Calls |       Ctx |    Out | Hit% | Cost $ |   Sec |
|--:|--------------------|------:|----------:|-------:|-----:|-------:|------:|
| 4 | Design handoff ... |    74 | 5,900,118 | 47,002 | 91.5 | 4.6330 | 610.3 |
| 5 | /compact ...       |     1 |   217,789 | 24,285 |  0.0 | 1.1780 | 240.2 |
| 6 | implement          |    77 | 9,168,612 | 33,681 | 97.7 | 4.3840 | 419.7 |


- **Calls** — API requests triggered by the prompt
- **Ctx** — context tokens processed; lower is usually cheaper and faster
- **Hit%** — context served from cache; higher is better
- **Cost** — estimated public API cost, useful for comparison rather than billing
- **Sec** — cumulative API time, not wall-clock time

Run an experiment's prompts inside **one** session. A fresh session starts with a cold
cache, so `Hit%` and `Cost` are only comparable within a session, never across them.

## Investigate a session

```bash
python3 ~/claude-otel/analyze.py \
  --session 8b5cbb08-7413-42ff-9615-f98338f48fac \
  --detail
```

Add `--html` for one merged table. Raw request and response bodies are stored in `otel-data/raw/`.

### Let AI analyze it

The easiest way to inspect a detailed report is to give it to an AI agent:

```bash
python3 ~/claude-otel/analyze.py \
  --session <ID> \
  --detail > telemetry-report.md
```

Attach telemetry-report.md to a fresh session and ask the agent to review the execution as a senior AI engineer. Mention that full request and response bodies are available in otel-data/raw/ if deeper investigation is needed.

The report may contain sensitive prompts, tool inputs, and repository content. Keep it local and out of Git.

## Stop

```bash
cd ~/claude-otel && docker compose stop
```

## Tested on

| Component | Version |
| --- | --- |
| Claude Code | 2.1.206 |
| OpenTelemetry Collector (contrib) | 0.158.0 |
| Python | 3.14.6 |
| Docker Compose | 5.1.4 |

Telemetry attribute names are not a stable API — a later Claude Code version may rename
or drop some, and `analyze.py` would then report zeros for those columns.

## Privacy

`otel-data/` contains prompts, repository content, raw API bodies, and account identifiers.

It is gitignored. **Keep it local.**


## Other Notes

The collector image comes from `ghcr.io` and is pinned to version `0.158.0` to reduce file-exporter schema drift.
