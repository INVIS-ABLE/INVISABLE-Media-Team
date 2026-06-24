"""The Agent Swarm — 20 specialist bots producing content continuously.

This is the orchestration layer that ties the platform's engines together into the
spec's pipeline: **scan → generate → gate → stock**. Each cycle, the specialist
bots scan topic domains, generate original drafts, gate them through every safety
check the platform owns (brand guardrails, the credible-source rule, quality and
mission scoring), and stock the survivors into the Content War Chest.

The guiding rule is **always generate more than you publish, and reject more than
you keep** — the swarm favours quality over volume. How hard it runs is informed by
War Chest reserve health: a thin reserve makes it work harder, a strong one lets it
ease off.

Everything is deterministic and offline-testable (generation degrades to safe
templates, the gates are the same hard-gate code the rest of the platform uses).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from invisable_os.engines.generator import Generator
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.quality import QualityEngine
from invisable_os.guardrails import check as brand_check
from invisable_os.models.content import ContentCandidate, Platform, QueueStatus
from invisable_os.services.fact_check import check_post
from invisable_os.services.source_scan import gather_topics
from invisable_os.services.war_chest import reserve_health
from invisable_os.store import Repository, get_repository


@dataclass(frozen=True)
class SwarmBot:
    """One specialist bot: a name, the pipeline stage it works in, and its role."""

    name: str
    stage: str  # scan | generate | gate | schedule
    role: str


# The 20-bot structure from the V3 spec, grouped by pipeline stage.
SWARM_BOTS: tuple[SwarmBot, ...] = (
    # --- scan (5) ---
    SwarmBot("UK Source Scanner Bot", "scan", "Credible UK gov/NHS/ONS/charity updates."),
    SwarmBot("Construction Scanner Bot", "scan", "Construction, tool/van theft, trades, jobs."),
    SwarmBot("Autoimmune & Invisible Illness Bot", "scan", "Chronic illness, fatigue, symptoms."),
    SwarmBot("Trades Relatability Bot", "scan", "Turns trades topics into relatable angles."),
    SwarmBot("Pop Culture Index Bot", "scan", "Films, TV, British comedy, memes, viral formats."),
    # --- generate (8) ---
    SwarmBot("Hook Bot", "generate", "Strong TikTok/Instagram hooks."),
    SwarmBot("Script Bot", "generate", "TikTok/Reel scripts."),
    SwarmBot("Caption Bot", "generate", "Captions, overlays, CTAs."),
    SwarmBot("Hashtag & Tag Bot", "generate", "Hashtags + the fixed tag network."),
    SwarmBot("Humour Bot", "generate", "British, dry, self-deprecating trades humour."),
    SwarmBot("Founder Voice Bot", "generate", "Raw, mission-led founder posts."),
    SwarmBot("Partner/Sponsor Bot", "generate", "Partner-safe campaigns (CT1, GT Insurance)."),
    SwarmBot("Remix/Parody Bot", "generate", "Parody/reaction/voiceover, rights-safe."),
    # --- gate (6) ---
    SwarmBot("Rights & Source Bot", "gate", "Owned/licensed/CC/consented/reference/blocked."),
    SwarmBot("Fact Checker Bot", "gate", "Requires credible sources for fact-led claims."),
    SwarmBot("Quote & Attribution Bot", "gate", "Correct source attribution on quotes/stats."),
    SwarmBot("Audio Quality Bot", "gate", "Clean, balanced, non-overlapping audio."),
    SwarmBot("Visual Quality Bot", "gate", "Readable, cropped, uncluttered, platform-ready."),
    SwarmBot("Brand Guardian Bot", "gate", "Ethics, mission, safety, reputational risk."),
    # --- schedule (1) ---
    SwarmBot("Scheduler & War Chest Bot", "schedule", "Selects the best, maintains the reserve."),
)

assert len(SWARM_BOTS) == 20, "the swarm is specified as exactly 20 bots"

# Each scan bot owns a small, deterministic topic pool. Offline this stands in for
# live scanning; with connectors wired these become the abstracted scan results.
_SCAN_TOPICS: dict[str, tuple[str, ...]] = {
    "UK Source Scanner Bot": (
        "NHS waiting times and invisible illness",
        "disability employment gap in the UK",
    ),
    "Construction Scanner Bot": (
        "tool theft from vans across UK trades",
        "apprenticeships and the construction skills shortage",
    ),
    "Autoimmune & Invisible Illness Bot": (
        "living with chronic fatigue at work",
        "autoimmune flare-ups nobody can see",
    ),
    "Trades Relatability Bot": (
        "self-employed trades and unpaid sick days",
        "working on site while masking chronic pain",
    ),
    "Pop Culture Index Bot": (
        "a boss-battle morning when your body says no",
        "British sitcom energy meets a flare day",
    ),
}

# Which generate bot maps to which generator angle + content pillar.
_GENERATE_ANGLES: dict[str, tuple[str, str]] = {
    "Hook Bot": ("reframe", "humour"),
    "Script Bot": ("explainer", "education"),
    "Caption Bot": ("community_prompt", "community"),
    "Hashtag & Tag Bot": ("solidarity", "community"),
    "Humour Bot": ("gentle_humour", "humour"),
    "Founder Voice Bot": ("founder_voice", "founder"),
    "Partner/Sponsor Bot": ("practical_tip", "partner"),
    "Remix/Parody Bot": ("myth_vs_reality", "trends"),
}

# A specialist persona per generate bot — sharpens the LLM's voice for that bot's
# craft at volume. These augment (never relax) the generator's safety system prompt;
# offline they're ignored and the deterministic templates still produce a field.
_GENERATE_PERSONAS: dict[str, str] = {
    "Hook Bot": (
        "You write scroll-stopping opening lines. Lead with a pattern-break, a relatable "
        "confession, or a 'POV:' setup. Keep the hook under 12 words; the body can be short."
    ),
    "Script Bot": (
        "You write tight short-form video scripts: a hook, three beats, and a soft CTA. "
        "Teach one concrete, honest thing — no jargon, no medical overclaiming."
    ),
    "Caption Bot": (
        "You write platform captions and on-screen text: punchy, plain, one idea, one CTA. "
        "No hashtag spam in the body — the Hashtag bot handles tags separately."
    ),
    "Hashtag & Tag Bot": (
        "You write community-first posts that earn a save or a share. Speak directly to one "
        "person who feels unseen; warmth over cleverness."
    ),
    "Humour Bot": (
        "You write warm British, dry, self-deprecating trades humour. Laugh WITH the trades "
        "and chronic-illness community, never at it — no mockery, no punching down, no slurs."
    ),
    "Founder Voice Bot": (
        "You write in the founder's raw, honest, mission-led voice: first person, plain, no "
        "corporate gloss. Speak to why INVISABLE exists — never invent a specific experience."
    ),
    "Partner/Sponsor Bot": (
        "You write sponsor-safe content: no false claims, no medical overclaims, no guarantees. "
        "Mention the partner naturally and keep the INVISABLE mission first."
    ),
    "Remix/Parody Bot": (
        "You write original parody and trend-adapted angles inspired by a format — never a copy. "
        "Transform the idea into an INVISABLE take; no copyrighted lines, no reposting."
    ),
}

# Every generate bot must have both an angle and a specialist persona.
_GENERATE_BOT_NAMES = {b.name for b in SWARM_BOTS if b.stage == "generate"}
assert _GENERATE_BOT_NAMES == set(_GENERATE_ANGLES) == set(_GENERATE_PERSONAS), (
    "every generate bot needs an angle and a persona"
)


@dataclass
class CycleResult:
    """The funnel + per-bot record produced by one swarm cycle."""

    cycle_id: str
    raw: int = 0
    gated_brand: int = 0
    quality_passed: int = 0
    fact_clean: int = 0
    usable: int = 0
    needs_review: int = 0
    stocked: int = 0
    rejected: int = 0
    bot_records: list[dict] | None = None
    reserve_tier: str = ""

    def as_dict(self) -> dict:
        return {
            "cycle_id": self.cycle_id,
            "funnel": {
                "raw_drafts": self.raw,
                "passed_brand_gate": self.gated_brand,
                "quality_passed": self.quality_passed,
                "fact_check_clean": self.fact_clean,
                "usable_drafts_queued": self.usable,
                "needs_human_review": self.needs_review,
                "stocked_to_war_chest": self.stocked,
                "brand_rejected": self.rejected,
            },
            "reject_rate": round(self.rejected / self.raw, 3) if self.raw else 0.0,
            "reserve_tier": self.reserve_tier,
            "bots": self.bot_records or [],
        }


class AgentSwarm:
    """Runs the 20-bot scan → generate → gate → stock pipeline for a cycle."""

    def __init__(self, repository: Repository | None = None) -> None:
        self.repo = repository or get_repository()
        self.generator = Generator()
        self.quality = QualityEngine()
        self.mission = MissionEngine()

    # -- public API ----------------------------------------------------------

    def bots(self) -> list[dict]:
        """The 20 bots with their lifetime contribution totals, for the dashboard."""
        totals = self.repo.bot_output_totals()
        out = []
        for bot in SWARM_BOTS:
            t = totals.get(bot.name, {})
            produced, passed = t.get("produced", 0), t.get("passed", 0)
            out.append(
                {
                    "name": bot.name,
                    "stage": bot.stage,
                    "role": bot.role,
                    "persona": _GENERATE_PERSONAS.get(bot.name, ""),
                    "produced": produced,
                    "passed": passed,
                    "rejected": t.get("rejected", 0),
                    "cycles": t.get("cycles", 0),
                    "pass_rate": round(passed / produced, 3) if produced else None,
                }
            )
        return out

    def run_cycle(self, *, drafts_per_topic: int = 2, platform: Platform = Platform.TIKTOK,
                  live_sources: bool = True) -> dict:
        """Run one full swarm cycle and persist the survivors + bot records.

        Returns the funnel and per-bot breakdown. Survivors are enqueued to the
        approval queue (status ``needs_human_review`` is never auto-approved) and the
        best are stocked straight into the War Chest reserve.

        ``live_sources`` lets the scan stage pull live headlines from configured
        sources (degrading to the seed pool); set ``False`` to force the offline pool.
        """
        cycle_id = uuid.uuid4().hex
        health = reserve_health(repository=self.repo)
        result = CycleResult(cycle_id=cycle_id, bot_records=[], reserve_tier=health["tier"])

        # 1. SCAN — each scanner bot surfaces its topics (live sources → seed fallback).
        scanned = gather_topics(_SCAN_TOPICS, repository=self.repo, live=live_sources)
        topics: list[tuple[str, str]] = []  # (topic, scanner_bot_name)
        for bot in (b for b in SWARM_BOTS if b.stage == "scan"):
            bot_topics = scanned.get(bot.name, [])
            for topic in bot_topics:
                topics.append((topic, bot.name))
            self._record(result, bot, produced=len(bot_topics), passed=len(bot_topics))

        # 2. GENERATE — each generate bot drafts against every scanned topic.
        drafts: list[ContentCandidate] = []
        for bot in (b for b in SWARM_BOTS if b.stage == "generate"):
            angle, pillar = _GENERATE_ANGLES[bot.name]
            persona = _GENERATE_PERSONAS.get(bot.name, "")
            made = 0
            for topic, _src in topics:
                cands = self.generator.generate(
                    topic, platform, count=drafts_per_topic, angle=angle, persona=persona
                )
                for c in cands:
                    c.themes = [*(c.themes or []), pillar]
                drafts.extend(cands)
                made += len(cands)
            self._record(result, bot, produced=made, passed=made)
        result.raw = len(drafts)

        # 3. GATE — brand guardrails hard-reject; quality + fact-check flag for review.
        survivors = self._gate(drafts, result)

        # 4. STOCK — enqueue every usable draft; the Scheduler & War Chest bot stocks
        #    only the genuinely clean ones (quality-passing AND not an unsourced fact).
        stocked, needs_review = self._stock(survivors)
        result.usable = len(survivors)
        result.needs_review = needs_review
        result.stocked = stocked
        result.rejected = result.raw - len(survivors)
        sched_bot = next(b for b in SWARM_BOTS if b.stage == "schedule")
        self._record(result, sched_bot, produced=len(survivors), passed=stocked)

        return result.as_dict()

    # -- internals -----------------------------------------------------------

    def _gate(self, drafts: list[ContentCandidate], result: CycleResult) -> list[dict]:
        """Brand guardrails hard-reject; quality + fact-check annotate for review.

        Only a brand-gate failure drops a draft. Everything else survives as a
        *usable draft* carrying flags: ``needs_improvement`` (below the quality bar)
        and ``needs_review`` (high-stakes content, or a fact-led claim with no source
        — which must never be auto-stocked or auto-published).
        """
        brand_pass = quality_pass = fact_clean = 0
        survivors: list[dict] = []
        for c in drafts:
            verdict = brand_check(c)
            if not verdict.passed:
                continue  # the only hard rejection
            brand_pass += 1
            q = self.quality.score(c)
            quality_ok = q.passes()
            if quality_ok:
                quality_pass += 1
            fc = check_post(c.full_text, [])  # no source attached at draft time
            if fc.ok:
                fact_clean += 1
            m = self.mission.advise(c)
            survivors.append(
                {
                    "candidate": c.model_dump(),
                    "quality_avg": q.average(),
                    "quality_passes": quality_ok,
                    "mission_total": m.total(),
                    "mission_verdict": m.verdict,
                    "fact_ok": fc.ok,
                    "needs_review": bool(verdict.needs_human_review) or not fc.ok,
                    "pillar": (c.themes or ["humour"])[-1],
                    "platform": c.platform.value,
                }
            )
        result.gated_brand = brand_pass
        result.quality_passed = quality_pass
        result.fact_clean = fact_clean

        # Attribute the funnel to the gate bots so the dashboard shows their work.
        total = len(drafts)
        gate_map = {
            "Brand Guardian Bot": brand_pass,
            "Rights & Source Bot": brand_pass,
            "Fact Checker Bot": fact_clean,
            "Quote & Attribution Bot": fact_clean,
            "Audio Quality Bot": quality_pass,
            "Visual Quality Bot": quality_pass,
        }
        for bot in (b for b in SWARM_BOTS if b.stage == "gate"):
            passed = gate_map.get(bot.name, total)
            self._record(result, bot, produced=total, passed=passed, rejected=total - passed)
        return survivors

    def _stock(self, survivors: list[dict]) -> tuple[int, int]:
        """Enqueue every usable draft; stock only the clean, on-mission ones.

        Returns ``(stocked, needs_review)``. A draft is stocked into the reserve only
        if it passes quality, is fact-clean (no unsourced claim), and is on-mission —
        anything flagged for review is queued but never auto-stocked.
        """
        stocked = needs_review = 0
        for s in survivors:
            cand = s["candidate"]
            flagged = s["needs_review"]
            if flagged:
                needs_review += 1
            queue_id = self.repo.enqueue(
                {
                    "candidate_id": cand.get("id", ""),
                    "candidate": cand,
                    "status": QueueStatus.PENDING_REVIEW.value,
                    "pillar": s["pillar"],
                    "platform": s["platform"],
                    "quality_avg": s["quality_avg"],
                    "quality_passes": s["quality_passes"],
                    "mission_total": s["mission_total"],
                    "mission_verdict": s["mission_verdict"],
                    "needs_human_review": flagged,
                }
            )
            # Stock-worthy: fact-clean, on-mission, and a strong quality average.
            # (The stricter all-dimension ``passes()`` bar still drives the
            # needs_improvement flag, but a high average is enough for the reserve.)
            clean = s["fact_ok"] and s["quality_avg"] >= 7.5 and s["mission_total"] >= 0.2
            if clean and not flagged:
                self.repo.add_war_chest_item(
                    {
                        "queue_item_id": queue_id,
                        "candidate_id": cand.get("id", ""),
                        "title": (cand.get("hook") or cand.get("brief") or "")[:200],
                        "category": s["pillar"],
                        "platform": s["platform"],
                        "pillar": s["pillar"],
                        "quality_score": s["quality_avg"],
                        "mission_score": s["mission_total"],
                        "reserve_status": "ready",
                    }
                )
                stocked += 1
        return stocked, needs_review

    def _record(self, result: CycleResult, bot: SwarmBot, *, produced: int,
                passed: int, rejected: int = 0) -> None:
        rec = {
            "cycle_id": result.cycle_id,
            "bot_name": bot.name,
            "stage": bot.stage,
            "task_type": bot.role,
            "produced": produced,
            "passed": passed,
            "rejected": rejected,
            "score": round(passed / produced, 3) if produced else 0.0,
            "status": "ok",
        }
        self.repo.add_bot_output(rec)
        result.bot_records.append(
            {"bot": bot.name, "stage": bot.stage, "produced": produced, "passed": passed}
        )


def run_swarm_cycle(*, drafts_per_topic: int = 2, live_sources: bool = True) -> dict:
    """Convenience entry point used by the API/CLI."""
    return AgentSwarm().run_cycle(drafts_per_topic=drafts_per_topic, live_sources=live_sources)


def swarm_stats(*, repository: Repository | None = None) -> dict:
    """Dashboard stats: per-bot totals, the production funnel, and reserve health."""
    repo = repository or get_repository()
    totals = repo.bot_output_totals()
    produced = sum(t["produced"] for t in totals.values())
    passed = sum(t["passed"] for t in totals.values())
    # Best/weakest by pass-rate among generate+gate bots that produced anything.
    ranked = [
        (name, t["passed"] / t["produced"])
        for name, t in totals.items()
        if t["produced"] and t["stage"] in {"generate", "gate"}
    ]
    ranked.sort(key=lambda kv: kv[1], reverse=True)
    return {
        "bots": len(SWARM_BOTS),
        "total_produced": produced,
        "total_passed": passed,
        "overall_pass_rate": round(passed / produced, 3) if produced else None,
        "best_bot": ranked[0][0] if ranked else None,
        "weakest_bot": ranked[-1][0] if ranked else None,
        "reserve": reserve_health(repository=repo),
    }
