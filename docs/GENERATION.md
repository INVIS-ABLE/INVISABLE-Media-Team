# Generation at Volume

How INVISABLE OS produces "hundreds of candidates daily" and selects only the best —
with a model when one is configured, deterministically when not.

## The pipeline (unchanged shape, smarter internals)

```
generate (structured JSON)  →  GUARDRAIL gate  →  deterministic score (whole field)
   →  improve top contenders  →  rank + dedup  →  LLM-judge re-score (top N only)
   →  select  →  founder rebalance  →  remember winners
```

## 1. Structured generation

The generator asks the model for a **JSON object** (`hook`, `body`, `call_to_action`)
rather than free text, via `LLMClient.complete_json`:

- **Claude** — prompted to return a single JSON object; the response is parsed with a
  tolerant `extract_json` (handles code fences / surrounding prose).
- **Ollama** — uses the native `format: "json"` constraint (Qwen/DeepSeek).
- **Offline / malformed** — falls back to a safe, original **template** so the field
  is never empty and the platform stays testable with no model.

Each daily slot generates in its **editorial angle** (see
[`DAILY_PIPELINE.md`](DAILY_PIPELINE.md)) so a day spans distinct content.

## 2. Deterministic floor (the whole field)

Every candidate is scored by the deterministic `Scorer` across the eight values. This
is fast enough to rank hundreds of candidates and can never be "talked around" — it
is the floor the judge sits on. Guardrails run first and are absolute.

## 3. LLM-judge (the shortlist only)

The judge ([`engines/judge.py`](../core/invisable_os/engines/judge.py)) is the
"expensive critic on the shortlist" pattern:

- It re-scores only the **top `judge_top` contenders** (default 8) a tournament has
  already shortlisted — bounding model calls to a handful per tournament, not per
  candidate.
- Its verdict is **blended 50/50** with the deterministic score (`JUDGE_BLEND`),
  never replacing it — a bad judge can't wreck the ranking, only nudge it.
- It returns structured JSON scores on the same eight value dimensions.

### Self-disabling

`LLMJudge.available` is `True` only when a Claude key is set or
`INVISABLE_USE_JUDGE=1`. Offline it is `False`, so:

- no model calls are made,
- the tournament is purely deterministic,
- tests stay fast and reproducible.

This means **enabling a model upgrades quality with zero code changes** — set
`ANTHROPIC_API_KEY` (or `OLLAMA_BASE_URL` + `INVISABLE_USE_JUDGE=1`) and the same
pipeline starts generating richer candidates and judging the shortlist.

## Cost shape at volume

| Stage | Model calls per tournament |
| ----- | -------------------------- |
| Generation | `count` (the field size) |
| Deterministic score | 0 |
| Improve | 0 |
| LLM-judge | ≤ `judge_top` (default 8) |

A full day (`DailyContentDirector`, 20 slots) therefore costs roughly
`20 × (count + 8)` model calls when live — generation dominates, judging is cheap.
