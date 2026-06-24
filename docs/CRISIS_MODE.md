# Crisis / Sensitive Topic Mode

> Some topics must never be treated like ordinary content.

When a piece touches a serious subject, the platform shifts into **crisis mode** and
raises hard requirements the pipeline and the approval UI must honour before it can
go out.

- Module: [`guardrails/crisis.py`](../core/invisable_os/guardrails/crisis.py)
- API: `POST /v1/crisis/check`

## Detected topics

`suicide_self_harm` · `death_bereavement` · `illness_deterioration` · `hospital` ·
`disability_discrimination` · `benefits_legal` · `abuse`

Detection is deterministic phrase-matching, deliberately conservative — it would
rather catch a sensitive topic than miss one.

## What crisis mode requires

For any sensitive piece:

| Requirement | Always | Notes |
| ----------- | :----: | ----- |
| **No jokes** | ✅ | humour treatment is off the table |
| **No clickbait** | ✅ | no curiosity-baiting a serious subject |
| **Human approval** | ✅ | never auto-published |
| **Credible source** | for factual/serious topics | suicide/self-harm, deterioration, hospital, discrimination, benefits/legal |
| **Signposting** | where appropriate | real UK support lines (below) |

Lived-experience grief/bereavement requires approval and signposting but **not** a
source (it isn't a factual claim).

## Signposting

Real, stable UK national support is attached per topic, e.g.:

- **Suicide / self-harm** — Samaritans 116 123 (free, 24/7); text SHOUT to 85258; 999 in an emergency.
- **Bereavement** — Cruse Bereavement Support 0808 808 1677.
- **Deterioration / terminal** — NHS 111; Marie Curie 0800 090 2309.
- **Discrimination at work** — Acas 0300 123 1100; Scope 0808 800 3333.
- **Benefits / legal** — Citizens Advice 0800 144 8848.
- **Abuse** — National Domestic Abuse Helpline 0808 2000 247.

## How it composes

`crisis_review(text)` returns a verdict (sensitive · topics · requirements ·
signposting) that sits alongside the brand guardrails and the
[Credible Source Rule](SOURCES.md). The swarm's gate and the approval screen can
consult it to force `needs_human_review`, block humour voices, and surface the
signposting — so the machine is careful exactly where it must be.
