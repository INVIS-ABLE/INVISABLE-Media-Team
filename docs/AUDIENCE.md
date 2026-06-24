# Audience Command — personas, voice bank, Hook Laboratory

> Not just *make content* — understand **who** is watching and answer in the right
> voice with the strongest possible hook.

Three deterministic, offline-testable engines that the rest of the platform targets
against. This is the first slice of the "Level 11" Audience Command + Growth
Intelligence upgrade.

- Engines: [`engines/audience.py`](../core/invisable_os/engines/audience.py),
  [`engines/hooks.py`](../core/invisable_os/engines/hooks.py)
- API: [`api/audience_routes.py`](../core/invisable_os/api/audience_routes.py)

## 1. Audience Persona Engine

Eight audiences every post can target — and a deterministic targeter that labels a
piece of content with its **primary** persona (there is always one; unmatched text
falls back to the general public).

| Persona | Who |
| ------- | --- |
| `trades_invisible_illness` | Tradesperson with an invisible illness |
| `self_employed_builder` | Self-employed builder — no sick pay |
| `family_carer` | Family member / carer |
| `employer_site_manager` | Employer / site manager |
| `sponsor_partner` | Sponsor / partner (CT1, GT Insurance) |
| `general_public` | General public |
| `young_chronic_illness` | Young person with chronic illness |
| `charity_supporter` | Charity supporter |

```
GET  /v1/personas              → the 8 personas (pains, platforms, tone)
POST /v1/personas/target       {text, platform?} → primary persona + runners-up
```

## 2. Hook Laboratory

For every post the lab generates **ten hooks** across ten types (shock truth · funny
pain · POV · confession · myth-bust · trades banter · founder raw · question ·
stitch/reaction · "nobody talks about…"), scores each on **six axes** — curiosity,
emotion, humour, shareability, platform-fit, mission-fit — and returns them
**best-first**. LLM-generated when configured; on-brand templates per type offline.

```
GET  /v1/hooks/types           → the 10 hook types + 6 score axes
POST /v1/hooks/lab             {topic, platform?, persona?} → 10 scored hooks + best
```

## 3. Creator Voice Bank

Nine stored voice modes so the feed never sounds samey, plus a `pick_voice` default
per pillar/persona (sponsor/partner always forces the sponsor-safe voice).

`stephen_raw` · `invisable_official` · `trades_banter` · `dark_humour_safe` ·
`emotional_charity` · `sponsor_safe` · `educational` · `pissed_off_professional` ·
`hope_mission`

```
GET  /v1/voices                → the 9 voice modes (id, label, brief)
POST /v1/voices/pick           {pillar?, persona?} → the chosen voice
```

## How it composes

A post → **target a persona** → **pick a voice** → **run the Hook Lab** for the
strongest opener. These are pure registries + scoring, so they slot into the swarm's
generate stage, the Studio, and the daily pipeline without new dependencies. Later
Level-11 slices (Format Split Testing, Comment War Room, Newsroom Mode, Content Decay,
Crisis Mode, Big Campaign, Failsafe/Backup) build on this foundation.
