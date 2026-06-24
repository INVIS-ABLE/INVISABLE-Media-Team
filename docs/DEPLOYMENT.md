# Deployment

INVISABLE OS is designed to be self-hosted on a single box (with a GPU for media
generation) and exposed safely via Cloudflare Tunnel.

## Prerequisites

- Docker + Docker Compose
- (optional) An NVIDIA GPU for ComfyUI/Flux and local Ollama models
- (optional) API keys: Anthropic (Claude), Firecrawl, ElevenLabs, Composio, Postiz

## 1. Configure

```bash
cp .env.example .env
# Fill in what you have. Everything has a safe default; the platform runs in a
# degraded-but-functional mode without keys.
```

## 2. Bring up the stack

```bash
# Minimal: API + structured + semantic memory
docker compose up -d core postgres chroma

# Add local LLMs + chat UI
docker compose --profile llm up -d

# Add media generation
docker compose --profile media up -d

# Add publishing + ops (Uptime Kuma, Watchtower)
docker compose --profile publish --profile ops up -d

# Everything
docker compose --profile llm --profile media --profile publish --profile ops up -d
```

Pull a local model once Ollama is up:

```bash
docker compose exec ollama ollama pull qwen2.5:14b
```

## 3. Verify

```bash
curl -s localhost:8080/health | jq
curl -s localhost:8080/v1/values | jq
```

| Service | URL |
| ------- | --- |
| Core API + docs | http://localhost:8080/docs |
| Open WebUI | http://localhost:3000 |
| n8n | http://localhost:5678 |
| ComfyUI | http://localhost:8188 |
| Uptime Kuma | http://localhost:3001 |

## 4. Expose securely

Use [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel) rather than
opening ports. Point the tunnel at `core:8080` (and the UIs you want reachable).
Keep Postgres and Chroma internal to the Docker network.

## 5. Operate

- **Watchtower** (container image) auto-updates images daily.
- **Uptime Kuma** monitors each service's health endpoint.
- Back up `postgres-data/`, `chroma/`, and `data/` regularly — that is the
  platform's accumulated memory.

## Running without Docker (development)

```bash
cd core
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn invisable_os.main:app --reload
```
