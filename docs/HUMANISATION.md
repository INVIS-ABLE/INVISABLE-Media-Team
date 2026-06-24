# Humanisation layer

> Strip the AI tells so the copy reads like a person wrote it.

Generated copy has a tell: stock clichés ("delve", "game-changer", "in today's
fast-paced world"), throat-clearing ("it's important to note that"), connective
scaffolding ("Furthermore,", "In conclusion,"), em-dash overuse, and emoji spam.
None of it sounds like a tradesperson talking straight.

This layer flags those tells and cleans them — a polish pass, not a rewrite.

- Module: [`services/humanise.py`](../core/invisable_os/services/humanise.py)
- API: `POST /v1/humanise`

## Two calls

```python
humanness_score(text)  # flag tells + score how human it reads (0–1)
humanise(text)         # return a cleaned version + score before/after
```

```
POST /v1/humanise  { "text": "Furthermore, we leverage cutting-edge tools…" }
  →
  { original, humanised, score_before, score_after, removed,
    tells_before:[{kind,match}], remaining_tells:[...] }
```

## What it flags

| Kind | Example |
| ---- | ------- |
| `cliche` | delve · leverage · game-changer · seamless · robust · ever-evolving · in today's fast-paced world |
| `emoji_spam` | more than 3 emoji |
| `em_dash_overuse` | more than 2 dashes |
| `ladder` | firstly / secondly / lastly |
| `not_only_but_also` | "not only … but also" |

The score starts at 1.0 and loses 0.12 per tell (floored at 0); `human` is
`true` at ≥ 0.8.

## What it cleans

Inflated phrases are swapped for plain ones (`leverage`→`use`,
`cutting-edge`→`modern`, `game-changer`→`big deal`, `utilise`→`use`), connective
scaffolding is removed (`Furthermore,`, `In conclusion,`), and em-dashes are
collapsed to commas. Whitespace and sentence capitalisation are tidied after each
removal, so the result reads clean. Meaning is never changed beyond swapping
inflated words for plain ones — running clean copy through it is a no-op.

It's a standalone layer: the approval UI or any caller can run a draft through it
before it goes near the queue. Deterministic and offline.
