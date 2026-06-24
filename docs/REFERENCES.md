# References & Licences

We studied ten open-source social schedulers as **architecture references** to
accelerate the build. Per the project's request, we checked each licence first and
follow this rule:

> **We do not copy code.** We learned the *patterns* (queue, calendar, media
> library, approval workflow, scheduler) and wrote original implementations.
> AGPL-3.0 projects are treated as **reference-only** so their copyleft never
> attaches to this proprietary codebase. Permissive (MIT/Apache-2.0) projects could
> have code imported with attribution, but we chose clean-room implementations for
> consistency.

## Licence audit (verified June 2026)

| Project | Licence | How we used it |
| ------- | ------- | -------------- |
| [Postiz](https://github.com/gitroomhq/postiz-app) | **AGPL-3.0** | reference only — overall self-hosted scheduler + provider abstraction |
| [TryPost](https://github.com/trypostit/trypost) | **AGPL-3.0** | reference only — Buffer/Hootsuite-style queue |
| [brightbean-studio](https://github.com/brightbeanxyz/brightbean-studio) | **AGPL-3.0** | reference only — management platform shape |
| [Mixpost](https://github.com/inovector/mixpost) | MIT | calendar + media library + multi-platform posting patterns |
| [OpenPost](https://github.com/rodrgds/openpost) | MIT | lightweight scheduling logic |
| [social-media-posts-scheduler](https://github.com/ClimenteA/social-media-posts-scheduler) | MIT | simple scheduler w/ TikTok/IG |
| [q8t](https://github.com/imbhargav5/q8t) | Apache-2.0 | calendar, bulk scheduling, AI creator flow |
| [Free-AI-Social-Media-Scheduler](https://github.com/Anil-matcha/Free-AI-Social-Media-Scheduler) | MIT | AI scheduler concept |
| [autopost-social-media](https://github.com/Hatalabdallah/autopost-social-media) | MIT | approval/automation workflow |
| [juzpost-cli](https://github.com/jackstiffer/juzpost-cli) | MIT | CLI posting/export commands |

> Licences can change — re-verify before importing any actual code from these repos.
> If we ever import permissive code, we will add the original `LICENSE` + attribution
> here and in the source file.

## Patterns we adopted (clean-room)

| Pattern | Where it lives in our code | Borrowed from |
| ------- | -------------------------- | ------------- |
| **Posting-slot queue** ("fill the next free slot") | `scheduling/engine.py` `next_open_slot`, `scheduling/defaults.py` | Buffer/Postiz/Mixpost |
| **Calendar view** (posts grouped by day) | `scheduling/engine.py` `calendar_by_day`, `GET /v1/calendar` | Mixpost/q8t |
| **Channels / connected accounts** | `models/scheduling.py`, `store` `ChannelRow` | all |
| **Approval workflow** (draft→approve→schedule→publish) | `models/content.py` `QueueStatus`, `store`, `services` | Postiz/Mixpost/autopost |
| **Media library** | `store` `MediaAssetRow`, `media/`, `GET /v1/media` | Mixpost/q8t |
| **Provider abstraction** (per-platform publisher) | `publish/` `Publisher` | Postiz |
| **CLI posting/automation** | `cli.py` (`schedule`, `calendar`, `produce`, `publish`) | juzpost-cli |

## Why clean-room

INVISABLE OS ships under a proprietary licence. A clean-room build keeps it free of
copyleft obligations, avoids attribution-tracking overhead across many small MIT
snippets, and lets every pattern be wired directly to *our* guardrails, mission
scoring, quality gate, and founder logic — which is where the real value is.
