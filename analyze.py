#!/usr/bin/env python3
"""Turn otel-data/logs.jsonl into one CSV row per human prompt.

Usage:
    python3 analyze.py [otel-data-dir] [-o out.csv] [--session SESSION_ID]

Groups claude_code.api_request records by prompt.id, since one human prompt
triggers several API requests when the agent loop makes tool calls.
"""

import argparse
import csv
import html
import json
import os
import sys
from collections import defaultdict

INT_ATTRS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "duration_ms",
)

COLUMNS = [
    "prompt_index",
    "session_id",
    "prompt_id",
    "started_at",
    "prompt_length",
    "prompt_preview",
    "api_calls",
    "models",
    "effort",
    "input_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "output_tokens",
    "context_tokens",
    "max_request_context",
    "cache_hit_ratio",
    "cost_usd",
    "duration_ms",
    "query_sources",
]


def attr_value(value):
    """Unwrap an OTLP AnyValue into a plain Python value."""
    if not value:
        return None
    for key, raw in value.items():
        if key in ("stringValue", "boolValue"):
            return raw
        if key in ("intValue", "doubleValue"):
            return raw
        return raw
    return None


def iter_log_records(path):
    with open(path, encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"skipping malformed line {line_no}: {exc}", file=sys.stderr)
                continue
            for resource in payload.get("resourceLogs", []):
                for scope in resource.get("scopeLogs", []):
                    for record in scope.get("logRecords", []):
                        attrs = {
                            a["key"]: attr_value(a.get("value"))
                            for a in record.get("attributes", [])
                        }
                        yield record.get("body", {}).get("stringValue"), attrs


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def render_markdown_table(headers, rows, aligns=None):
    """GFM pipe table, padded with spaces so it also lines up in a plain terminal."""
    aligns = aligns or ["l"] * len(headers)
    widths = [max(len(h), 3) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells):
        padded = (cell.rjust(widths[i]) if aligns[i] == "r" else cell.ljust(widths[i]) for i, cell in enumerate(cells))
        return "| " + " | ".join(padded) + " |"

    def sep_cell(i):
        dashes = "-" * widths[i]
        return dashes[:-1] + ":" if aligns[i] == "r" else dashes

    lines = [fmt_row(headers), "|" + "|".join(f" {sep_cell(i)} " for i in range(len(headers))) + "|"]
    lines.extend(fmt_row(row) for row in rows)
    return lines



def collect(path, session_filter=None):
    prompts = {}
    requests = defaultdict(list)

    for name, attrs in iter_log_records(path):
        prompt_id = attrs.get("prompt.id")
        if not prompt_id:
            continue
        if session_filter and attrs.get("session.id") != session_filter:
            continue
        if name == "claude_code.user_prompt":
            prompts[prompt_id] = attrs
        elif name == "claude_code.api_request":
            requests[prompt_id].append(attrs)

    return prompts, requests


def collect_session_events(path, session_id):
    """All request/response/prompt events for one session.id, in original order."""
    prompts = {}
    events = []
    detail_names = (
        "claude_code.api_request",
        "claude_code.api_request_body",
        "claude_code.api_response_body",
        "claude_code.assistant_response",
    )

    for name, attrs in iter_log_records(path):
        if attrs.get("session.id") != session_id:
            continue
        if name == "claude_code.user_prompt":
            prompts[attrs.get("prompt.id")] = attrs
        elif name in detail_names:
            events.append((name, attrs))

    events.sort(key=lambda pair: as_int(pair[1].get("event.sequence")))
    return prompts, events


def load_json_safe(path):
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def extract_tool_uses(response_body):
    """[{id, name, input}, ...] for every tool call the model made in this response."""
    if not response_body:
        return []
    return [
        {"id": block.get("id"), "name": block.get("name"), "input": block.get("input")}
        for block in response_body.get("content", []) or []
        if isinstance(block, dict) and block.get("type") == "tool_use"
    ]


def extract_tool_results(request_body):
    """{tool_use_id: content} for every tool_result present in this request's messages."""
    results = {}
    if not request_body:
        return results
    for message in request_body.get("messages", []) or []:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                results[block.get("tool_use_id")] = block.get("content")
    return results


def format_tool_input(tool_input, limit=90):
    text = json.dumps(tool_input, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "..."


def format_tool_result(content, limit=90):
    if isinstance(content, list):
        text = " ".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        )
    else:
        text = str(content or "")
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + f"...({len(text)} chars)"


def render_html_detail_table(metric_rows, detail_rows):
    """One HTML table: each call's metrics span its trace rows via rowspan."""
    by_call = defaultdict(list)
    for row in detail_rows:
        by_call[row[0]].append(row)

    headers = ["Call", "Model", "Eff", "Ctx", "Out", "Cost $", "Sec", "Dir", "Kind", "Tool / Id", "Detail", "Ref"]
    lines = ["<table>", "<thead>", "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>", "</thead>", "<tbody>"]

    def esc(value):
        return html.escape(str(value), quote=True)

    for metric in metric_rows:
        call, model, effort, ctx, out, cost, ms = metric
        if not call.strip():  # skip the markdown-only Total row
            continue
        sec = f"{int(ms.replace(',', '') or '0') / 1000:.1f}"
        trace = by_call.get(call) or [[call, "", "", "", "", ""]]
        span = len(trace)
        metric_cells = (
            f'<td rowspan="{span}" align="right">{esc(call)}</td>'
            f'<td rowspan="{span}">{esc(model)}</td>'
            f'<td rowspan="{span}">{esc(effort)}</td>'
            f'<td rowspan="{span}" align="right">{esc(ctx)}</td>'
            f'<td rowspan="{span}" align="right">{esc(out)}</td>'
            f'<td rowspan="{span}" align="right">{esc(cost)}</td>'
            f'<td rowspan="{span}" align="right">{esc(sec)}</td>'
        )
        for i, (_, direction, kind, tool, detail, ref) in enumerate(trace):
            trace_cells = (
                f"<td>{esc(direction)}</td>"
                f"<td>{esc(kind)}</td>"
                f"<td>{esc(tool)}</td>"
                f"<td>{esc(detail)}</td>"
                f"<td>{esc(ref)}</td>"
            )
            lines.append("<tr>" + (metric_cells if i == 0 else "") + trace_cells + "</tr>")

    lines += ["</tbody>", "</table>"]
    return lines


def print_session_detail(data_dir, session_id, as_html=False):
    logs = os.path.join(data_dir, "logs.jsonl")
    prompts, events = collect_session_events(logs, session_id)
    if not events:
        print(f"no events found for session.id {session_id}", file=sys.stderr)
        return

    first_prompt = next(iter(prompts.values()), {})
    first_preview = (first_prompt.get("prompt") or "").replace("\n", " ") or ""
    if len(first_preview) > 100:
        first_preview = first_preview[:97] + "..."
    if first_preview:
        print(f"## Session `{session_id}` — {first_preview}\n")
    else:
        print(f"## Session `{session_id}`\n")

    seen_prompts = []
    by_prompt = defaultdict(list)
    for name, attrs in events:
        pid = attrs.get("prompt.id")
        if pid not in by_prompt:
            seen_prompts.append(pid)
        by_prompt[pid].append((name, attrs))

    printed_result_ids = set()  # request bodies replay the whole history; only show new results
    for pid in seen_prompts:
        prompt = prompts.get(pid, {})
        preview = (prompt.get("prompt") or "").replace("\n", " ") or pid
        print(f"### Message: {preview}\n")

        table_rows = []
        detail_rows = []
        pending_tool_results = {}
        request_ref = None
        response_ref = None
        call_no = 0
        total_out = total_cost = total_ms = 0
        for name, attrs in by_prompt[pid]:
            if name == "claude_code.api_request_body":
                request_ref = attrs.get("body_ref")
                pending_tool_results = extract_tool_results(load_json_safe(request_ref))
            elif name == "claude_code.api_request":
                call_no += 1
                ctx = (
                    as_int(attrs.get("input_tokens"))
                    + as_int(attrs.get("cache_read_tokens"))
                    + as_int(attrs.get("cache_creation_tokens"))
                )
                total_out += as_int(attrs.get("output_tokens"))
                total_cost += as_float(attrs.get("cost_usd"))
                total_ms += as_int(attrs.get("duration_ms"))
                table_rows.append(
                    [
                        str(call_no),
                        attrs.get("model") or "",
                        attrs.get("effort") or "-",
                        f"{ctx:,}",
                        f"{as_int(attrs.get('output_tokens')):,}",
                        f"{as_float(attrs.get('cost_usd')):.4f}",
                        f"{as_int(attrs.get('duration_ms')):,}",
                    ]
                )
                for tool_use_id, content in pending_tool_results.items():
                    if tool_use_id in printed_result_ids:
                        continue
                    printed_result_ids.add(tool_use_id)
                    short_id = (tool_use_id or "")[:12]
                    detail_rows.append(
                        [
                            str(call_no),
                            "\u2190",
                            "result",
                            short_id,
                            format_tool_result(content),
                            os.path.relpath(request_ref, data_dir) if request_ref else "",
                        ]
                    )
                pending_tool_results = {}
            elif name == "claude_code.api_response_body":
                response_ref = attrs.get("body_ref")
                response_body = load_json_safe(response_ref)
                for tool in extract_tool_uses(response_body):
                    detail_rows.append(
                        [
                            str(call_no),
                            "\u2192",
                            "tool_use",
                            tool["name"] or "",
                            format_tool_input(tool["input"]),
                            os.path.relpath(response_ref, data_dir) if response_ref else "",
                        ]
                    )
            elif name == "claude_code.assistant_response":
                text = (attrs.get("response") or "").replace("\n", " ")
                if text:
                    detail_rows.append(
                        [
                            str(call_no),
                            "\u2192",
                            "says",
                            "assistant",
                            text[:90] + ("..." if len(text) > 90 else ""),
                            os.path.relpath(response_ref, data_dir) if response_ref else "",
                        ]
                    )

        if table_rows:
            table_rows.append(
                [
                    "",
                    "**Total**",
                    "",
                    "",
                    f"{total_out:,}",
                    f"{total_cost:.4f}",
                    f"{total_ms:,}",
                ]
            )
        time_spent = (
            f"**Time spent:** {total_ms / 1000:,.1f} s "
            f"({total_ms / 60000:.1f} min) across {call_no} API calls\n"
        )
        if as_html:
            for line in render_html_detail_table(table_rows, detail_rows):
                print(line)
            print()
            print(time_spent)
            continue
        for line in render_markdown_table(
            ["Call", "Model", "Eff", "Ctx", "Out", "Cost $", "Ms"],
            table_rows,
            aligns=["r", "l", "l", "r", "r", "r", "r"],
        ):
            print(line)
        print()
        print(time_spent)
        if detail_rows:
            for line in render_markdown_table(
                ["Call", "Dir", "Kind", "Tool / Id", "Detail", "Ref (full content)"],
                detail_rows,
                aligns=["r", "l", "l", "l", "l", "l"],
            ):
                print(line)
            print()




def build_rows(prompts, requests):
    rows = []
    for prompt_id, calls in requests.items():
        calls.sort(key=lambda a: as_int(a.get("event.sequence")))
        prompt = prompts.get(prompt_id, {})

        totals = {key: sum(as_int(c.get(key)) for c in calls) for key in INT_ATTRS}
        cost = sum(as_float(c.get("cost_usd")) for c in calls)
        per_call_context = [
            as_int(c.get("input_tokens"))
            + as_int(c.get("cache_read_tokens"))
            + as_int(c.get("cache_creation_tokens"))
            for c in calls
        ]
        context = sum(per_call_context)
        cache_read = totals["cache_read_tokens"]

        preview = (prompt.get("prompt") or "").replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:77] + "..."

        rows.append(
            {
                "session_id": calls[0].get("session.id", ""),
                "prompt_id": prompt_id,
                "started_at": prompt.get("event.timestamp")
                or calls[0].get("event.timestamp", ""),
                "prompt_length": prompt.get("prompt_length", ""),
                "prompt_preview": preview,
                "api_calls": len(calls),
                "models": "|".join(
                    sorted({c.get("model", "") for c in calls if c.get("model")})
                ),
                "effort": "|".join(
                    sorted({c.get("effort", "") for c in calls if c.get("effort")})
                ),
                "input_tokens": totals["input_tokens"],
                "cache_read_tokens": cache_read,
                "cache_creation_tokens": totals["cache_creation_tokens"],
                "output_tokens": totals["output_tokens"],
                "context_tokens": context,
                "max_request_context": max(per_call_context) if per_call_context else 0,
                "cache_hit_ratio": round(cache_read / context, 4) if context else 0.0,
                "cost_usd": round(cost, 6),
                "duration_ms": totals["duration_ms"],
                "query_sources": "|".join(
                    sorted({c.get("query_source", "") for c in calls if c.get("query_source")})
                ),
            }
        )

    # group by session (contiguous), but order the sessions themselves by when they started -
    # session_id is a random UUID, so sorting by it directly scrambles chronological order.
    session_start = {}
    for row in rows:
        sid = row["session_id"]
        if sid not in session_start or row["started_at"] < session_start[sid]:
            session_start[sid] = row["started_at"]
    rows.sort(key=lambda r: (session_start[r["session_id"]], r["session_id"], r["started_at"]))
    for index, row in enumerate(rows, 1):
        row["prompt_index"] = index
    return rows


LEGEND_ROWS = [
    ["#", "message index (order in the table)"],
    ["Prompt", "preview of what you typed"],
    ["Calls", "API requests this message triggered (tool-call round trips count as extra calls)"],
    ["Model", "model(s) the API calls ran on (| separated if mixed, e.g. after a subagent or fallback)"],
    ["Eff", "reasoning effort level the model ran with (thinking budget varies per level, so cost does too)"],
    ["Ctx", "context tokens sent (input + cache_read + cache_creation); lower is cheaper/faster"],
    ["Out", "output tokens Claude generated"],
    ["Hit%", "cache_read_tokens / Ctx; higher is better (more served from cache, not rebuilt)"],
    ["Cost $", "USD cost of this message (summed across its API calls)"],
    ["Ms", "total API duration in ms (summed across its API calls); lower is faster"],
    ["Sec", "total API time in seconds (duration_ms / 1000)"],
]

TABLE_HEADERS = ["#", "Prompt", "Calls", "Model", "Eff", "Ctx", "Out", "Hit%", "Cost $", "Ms", "Sec"]
TABLE_ALIGNS = ["r", "l", "r", "l", "l", "r", "r", "r", "r", "r", "r"]


def _table_row(row):
    preview = row["prompt_preview"]
    if len(preview) > 40:
        preview = preview[:37] + "..."
    return [
        str(row["prompt_index"]),
        preview,
        str(row["api_calls"]),
        row["models"] or "-",
        row["effort"] or "-",
        f"{row['context_tokens']:,}",
        f"{row['output_tokens']:,}",
        f"{row['cache_hit_ratio'] * 100:.1f}",
        f"{row['cost_usd']:.4f}",
        f"{row['duration_ms']:,}",
        f"{row['duration_ms'] / 1000:,.1f}",
    ]


def _totals_row(label, rows):
    return [
        "",
        label,
        str(sum(r["api_calls"] for r in rows)),
        "",
        "",
        f"{sum(r['context_tokens'] for r in rows):,}",
        f"{sum(r['output_tokens'] for r in rows):,}",
        "",
        f"{sum(r['cost_usd'] for r in rows):.4f}",
        f"{sum(r['duration_ms'] for r in rows):,}",
        f"{sum(r['duration_ms'] for r in rows) / 1000:,.1f}",
    ]


def print_summary(rows):
    if not rows:
        print("no claude_code.api_request records found", file=sys.stderr)
        return

    print("## Legend\n")
    for line in render_markdown_table(["Column", "Meaning"], LEGEND_ROWS):
        print(line)
    print()

    last_session = None
    session_rows = []

    def flush_session(session_id, srows):
        first_prompt = (srows[0]["prompt_preview"] or "").replace("|", "\\|") or "-"
        print(f"### Session `{session_id}` — {first_prompt}\n")
        table_rows = [_table_row(r) for r in srows]
        table_rows.append(_totals_row("**Total**", srows))
        for line in render_markdown_table(TABLE_HEADERS, table_rows, aligns=TABLE_ALIGNS):
            print(line)
        print()

    for row in rows:
        if row["session_id"] != last_session:
            if session_rows:
                flush_session(last_session, session_rows)
            session_rows = []
        last_session = row["session_id"]
        session_rows.append(row)
    if session_rows:
        flush_session(last_session, session_rows)

    print("## Grand Total\n")
    for line in render_markdown_table(
        TABLE_HEADERS, [_totals_row("**All sessions**", rows)], aligns=TABLE_ALIGNS
    ):
        print(line)




def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "data_dir",
        nargs="?",
        default=os.environ.get(
            "CLAUDE_OTEL_DATA", os.path.join(os.path.dirname(__file__), "otel-data")
        ),
    )
    parser.add_argument("-o", "--out", help="CSV output path (default: <data_dir>/prompts.csv)")
    parser.add_argument("--session", help="only include this session.id")
    parser.add_argument(
        "--detail",
        action="store_true",
        help="with --session, print a call-by-call drilldown (tool calls, inputs, results) "
        "for that session instead of writing the CSV summary",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="with --detail, emit one merged HTML table (metrics + trace, "
        "rowspan-grouped per call) instead of two Markdown tables",
    )
    args = parser.parse_args()

    logs = os.path.join(args.data_dir, "logs.jsonl")
    if not os.path.exists(logs):
        parser.error(f"{logs} not found")

    if args.html and not args.detail:
        parser.error("--html requires --detail")

    if args.detail:
        if not args.session:
            parser.error("--detail requires --session SESSION_ID")
        print_session_detail(args.data_dir, args.session, as_html=args.html)
        return

    prompts, requests = collect(logs, args.session)
    rows = build_rows(prompts, requests)

    out = args.out or os.path.join(args.data_dir, "prompts.csv")
    with open(out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print_summary(rows)
    print(f"\nwrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
