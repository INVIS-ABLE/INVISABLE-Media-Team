# Evaluation layer

> One scorecard across every gate the platform owns.

DeepEval / Promptfoo / Ragas-style evaluation, but **deterministic and offline**:
take a piece of copy and run it through the whole battery at once, and get back a
single scorecard — a pass/fail per metric, an overall verdict, and a letter grade.

- Module: [`services/evaluation.py`](../core/invisable_os/services/evaluation.py)
- API: `POST /v1/evaluate`

## The battery

| Metric | What it checks | Source |
| ------ | -------------- | ------ |
| `brand_safety` | passes the hard brand gate | guardrails |
| `fact_grounded` | fact-led claims have a credible source | [Credible Source Rule](SOURCES.md) |
| `mission_aligned` | on-mission (total ≥ 0.2) | Mission engine |
| `quality` | quality average clears the bar | Quality engine |
| `humanness` | few/no AI tells (≥ 0.8) | [Humanisation layer](HUMANISATION.md) |
| `crisis_care` | not a sensitive topic — or flagged for human approval + signposting | [Crisis Mode](CRISIS_MODE.md) |

Because it composes the real engines, the scorecard reflects exactly what the live
pipeline enforces — it's the seam an eval suite or a CI gate hooks into.

## Surface

```
POST /v1/evaluate
  { "text": "Tool theft rose 20% last year.",
    "sources": [{"name":"ONS","source_type":"gov"}],
    "platform": "instagram", "content_format": "text_post" }
  →
  { overall_pass, pass_rate, grade, passed, total,
    metrics: [ { name, score, passed, detail } ],
    sensitive, signposting }
```

`evaluate_batch(items)` runs a set (strings, or dicts with `text` / `sources` /
`platform` / `content_format`) and reports `fully_passing` and `avg_pass_rate`
with an aggregate grade. Grades: A ≥ 0.95, B ≥ 0.8, C ≥ 0.6, D ≥ 0.4, else F.

A sensitive piece "fails" `crisis_care` deliberately — that's the layer refusing
to wave through anything that needs a human and signposting first.
