# `invisable-os` — core application

The Python application at the heart of the INVISABLE® AI Media Agency OS. See the
[repository README](../README.md) for the full picture and
[`docs/`](../docs/) for architecture, values, engines, and deployment.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn invisable_os.main:app --reload   # http://localhost:8080/docs
```

## Layout

| Path | Purpose |
| ---- | ------- |
| `invisable_os/guardrails/` | The Prime Directive, encoded as a hard gate. |
| `invisable_os/engines/` | Tournament, Watchtower, Cultural, Harvester, Founder, Engagement. |
| `invisable_os/brain/` | `INVISABLE_BRAIN` shared memory (ChromaDB + local fallback). |
| `invisable_os/llm/` | Claude + Ollama clients with graceful degradation. |
| `invisable_os/models/` | Domain models (content, scoring, metrics). |
| `invisable_os/services/` | Operational seams: pipeline, scheduling, publishing, [Agent Swarm](../docs/AGENT_SWARM.md), [War Chest](../docs/WAR_CHEST.md), [credible-source fact-check](../docs/SOURCES.md). |
| `invisable_os/api/` | FastAPI orchestration surface. |
| `tests/` | Deterministic engine + guardrail tests. |

Every external dependency degrades gracefully: with no API keys or services the
platform still runs and the full test suite passes.
