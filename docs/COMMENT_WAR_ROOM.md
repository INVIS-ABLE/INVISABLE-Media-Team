# Comment War Room

> Sort the noise so the comments that matter rise to the top.

A busy post draws warm support, genuine questions, the odd troll, spam, and —
sometimes — someone quietly reaching out in crisis. The War Room triages the lot:
it classifies each comment, prioritises it, picks an action, and drafts a
guardrail-safe reply where one is warranted.

- Module: [`services/comment_war_room.py`](../core/invisable_os/services/comment_war_room.py)
- API: `POST /v1/engagement/war-room`

## Categories, priority, and action

| Category | Priority | Action | Reply? |
| -------- | :------: | ------ | ------ |
| `crisis` | 1 | **escalate** to a human | never auto-reply; signposting attached |
| `lead` | 2 | **escalate** to founder / partnerships | no |
| `question` | 3 | **reply** | vetted supportive reply |
| `support` | 4 | **reply** | warm thank-you |
| `neutral` | 5 | **reply** | light acknowledgement |
| `abuse` | 6 | **do_not_engage** | no |
| `spam` | 7 | **ignore** | no |

First match wins, and **crisis always trumps everything** — a comment that trips
[Crisis Mode](CRISIS_MODE.md) is escalated to a human with real UK signposting,
and is *never* auto-replied. Abuse and spam are filtered out before any reply is
considered.

Every drafted reply is run back through the brand guardrails before it's offered
(`reply_approved`), so the War Room can never hand back something off-brand.

## Surface

```
POST /v1/engagement/war-room
  { "comments": ["I felt suicidal", "thanks, this helped", "buy now www.x.com"],
    "platform": "instagram" }
  →
  { total, by_category, by_action, escalations,
    comments: [ { text, category, priority, action, reply, reply_approved,
                  sensitive, topics, signposting } ] }
```

`comments` accepts plain strings or `{ "text": ... }` objects. Results come back
**sorted most-important-first**, so the founder works top-down: crises and leads,
then questions, then the rest. Detection is deterministic phrase-matching and
reuse of Crisis Mode; everything runs offline.
