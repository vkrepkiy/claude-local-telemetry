# Manual setup

Start Rancher Desktop, then verify `docker info` works.

1. `mkdir -p ~/claude-otel/otel-data/raw && cd ~/claude-otel`
2. Add `compose.yaml`, `otel-collector.yaml`, `env.sh` (already in this repo).
   - Image is pulled from **ghcr.io**, not Docker Hub — `registry-1.docker.io`
     times out on the BestSecret network.
   - Collector version is pinned (`0.158.0`); the file exporter is alpha, so an
     unpinned tag risks schema drift.
3. `docker compose up -d` — `docker compose logs collector` must end with
   "Everything is ready."
4. From any repository you want to measure:

   ```bash
   source ~/claude-otel/env.sh && claude
   ```

5. Analyze: `python3 ~/claude-otel/analyze.py`
6. Stop: `cd ~/claude-otel && docker compose stop`

Do all test prompts inside **one** session — a fresh session starts with a cold
prompt cache, so cache-hit numbers across sessions are not comparable.

`otel-data/` holds prompts, raw request bodies, and account identifiers. It is
gitignored; keep it local.
