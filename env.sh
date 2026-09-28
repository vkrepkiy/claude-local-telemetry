# Telemetry environment for Claude Code. Source before launching claude:
#   source /path/to/claude-local-telemetry/env.sh
# Or skip it entirely and use ./claude-telemetry, which sources this for you.

# Resolve this file's own directory, so the checkout can live anywhere.
# The eval hides zsh-only syntax from bash's parser.
if [ -n "${ZSH_VERSION:-}" ]; then
  _claude_otel_src=$(eval 'echo "${(%):-%x}"')
else
  _claude_otel_src="${BASH_SOURCE[0]:-$0}"
fi
export CLAUDE_OTEL_DATA="$(cd "$(dirname "$_claude_otel_src")" && pwd)/otel-data"
unset _claude_otel_src
mkdir -p "$CLAUDE_OTEL_DATA/raw"

export CLAUDE_CODE_ENABLE_TELEMETRY=1
export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1

export OTEL_TRACES_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318

export OTEL_METRIC_EXPORT_INTERVAL=1000
export OTEL_LOGS_EXPORT_INTERVAL=1000
export OTEL_TRACES_EXPORT_INTERVAL=1000
export OTEL_METRICS_INCLUDE_SESSION_ID=true
export OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=delta

export OTEL_LOG_USER_PROMPTS=1
export OTEL_LOG_TOOL_DETAILS=1
export OTEL_LOG_RAW_API_BODIES="file:${CLAUDE_OTEL_DATA}/raw"

# Isolation — off by default, so you measure your real setup. Uncomment to
# strip a session down to a clean baseline when comparing runs.
# export CLAUDE_CODE_SKIP_PROMPT_HISTORY=1      # don't persist the transcript
# export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1      # no personal/project auto-memory
# export CLAUDE_CODE_DISABLE_CLAUDE_MDS=1       # no CLAUDE.md auto-discovery
# export CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 # no background task prefetches
