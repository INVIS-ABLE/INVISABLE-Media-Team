"""Content Decay Detector — old content expires; sameness is flagged.

A feed rots in predictable ways: the same hook gets reused, two posts say nearly the
same thing, reserve stock ages past its shelf life, one category crowds out the rest,
and a handful of hashtags get worn out. This detector scans the approval queue and the
War Chest reserve and surfaces those decay signals so the founder (and the scheduler)
can refresh before the audience notices.

It is read-only and deterministic — counting, set-overlap and dates, no model — so it
is fast and fully testable offline. It flags; it never deletes.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime

from invisable_os.store import Repository, get_repository

# Thresholds (deliberately simple and explainable).
_HOOK_REUSE_FLAG = 3          # same hook used this many times → overused
_DUPLICATE_JACCARD = 0.6      # token overlap above this → too similar
_CATEGORY_DOMINANCE = 0.5     # one category > this share of ready reserve → crowding
_HASHTAG_SHARE = 0.5          # a hashtag in > this share of recent posts → stale
_RECENT_LIMIT = 200           # how many recent queue items to consider
_MIN_FOR_SHARE = 6            # don't cry "dominance" on a tiny sample

_STOP = frozenset(
    "the a an and or but if then of to in on at for with you your we our it is are be "
    "this that what when why how me my i".split()
)


def _now() -> datetime:
    return datetime.now(UTC)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9']+", (text or "").lower()) if w not in _STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class DecayFlag:
    kind: str          # overused_hook | near_duplicate | expired_reserve | …
    severity: str      # low | medium | high
    detail: str
    refs: list[str] = field(default_factory=list)  # queue/war-chest item ids

    def as_dict(self) -> dict:
        return {"kind": self.kind, "severity": self.severity, "detail": self.detail,
                "refs": self.refs}


@dataclass
class DecayReport:
    flags: list[DecayFlag] = field(default_factory=list)
    scanned_queue: int = 0
    scanned_reserve: int = 0

    def add(self, flag: DecayFlag) -> None:
        self.flags.append(flag)

    def as_dict(self) -> dict:
        by_kind: dict[str, int] = Counter(f.kind for f in self.flags)
        return {
            "ok": not self.flags,
            "scanned": {"queue": self.scanned_queue, "reserve": self.scanned_reserve},
            "flag_count": len(self.flags),
            "by_kind": dict(by_kind),
            "flags": [f.as_dict() for f in self.flags],
        }


def detect_decay(*, repository: Repository | None = None) -> DecayReport:
    """Scan recent content for decay signals and return a flag report."""
    repo = repository or get_repository()
    queue = repo.list_queue(limit=_RECENT_LIMIT)
    reserve = repo.list_war_chest(reserve_status="ready", limit=500)
    report = DecayReport(scanned_queue=len(queue), scanned_reserve=len(reserve))

    _flag_repeated_hooks(queue, report)
    _flag_near_duplicates(queue, report)
    _flag_overused_hashtags(queue, report)
    _flag_expired_reserve(reserve, report)
    _flag_category_dominance(reserve, report)
    return report


def _flag_repeated_hooks(queue: list[dict], report: DecayReport) -> None:
    by_hook: dict[str, list[str]] = {}
    for it in queue:
        hook = _norm((it.get("candidate") or {}).get("hook", ""))
        if hook:
            by_hook.setdefault(hook, []).append(it["id"])
    for hook, ids in by_hook.items():
        if len(ids) >= _HOOK_REUSE_FLAG:
            report.add(DecayFlag(
                "overused_hook",
                "high" if len(ids) >= _HOOK_REUSE_FLAG * 2 else "medium",
                f"Hook reused {len(ids)}×: “{hook[:60]}”",
                ids[:10],
            ))


def _flag_near_duplicates(queue: list[dict], report: DecayReport) -> None:
    docs = []
    for it in queue[:80]:  # bound the O(n^2) comparison
        c = it.get("candidate") or {}
        toks = _tokens(f"{c.get('hook', '')} {c.get('body', '')}")
        if toks:
            docs.append((it["id"], toks))
    seen_pairs = 0
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            if _jaccard(docs[i][1], docs[j][1]) >= _DUPLICATE_JACCARD:
                report.add(DecayFlag(
                    "near_duplicate", "medium",
                    "Two recent posts are near-identical in wording.",
                    [docs[i][0], docs[j][0]],
                ))
                seen_pairs += 1
                if seen_pairs >= 20:  # cap noise
                    return


def _flag_overused_hashtags(queue: list[dict], report: DecayReport) -> None:
    total = 0
    counts: Counter[str] = Counter()
    for it in queue:
        c = it.get("candidate") or {}
        tags = c.get("hashtags") or it.get("tags") or []
        if not tags:
            continue
        total += 1
        for t in {str(t).lower() for t in tags}:
            counts[t] += 1
    if total < _MIN_FOR_SHARE:
        return
    for tag, n in counts.items():
        if n / total > _HASHTAG_SHARE:
            report.add(DecayFlag(
                "stale_hashtag", "low",
                f"Hashtag {tag} appears on {round(100 * n / total)}% of recent posts.",
            ))


def _flag_expired_reserve(reserve: list[dict], report: DecayReport) -> None:
    now = _now()
    expired: list[str] = []
    for it in reserve:
        exp = it.get("expiry_date")
        if not exp:
            continue
        try:
            when = datetime.fromisoformat(exp)
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        if when < now:
            expired.append(it["id"])
    if expired:
        report.add(DecayFlag(
            "expired_reserve",
            "high" if len(expired) >= 10 else "medium",
            f"{len(expired)} War Chest item(s) past their expiry date — refresh or retire.",
            expired[:20],
        ))


def _flag_category_dominance(reserve: list[dict], report: DecayReport) -> None:
    if len(reserve) < _MIN_FOR_SHARE:
        return
    counts: Counter[str] = Counter(it.get("category", "evergreen") for it in reserve)
    top, n = counts.most_common(1)[0]
    share = n / len(reserve)
    if share > _CATEGORY_DOMINANCE:
        report.add(DecayFlag(
            "category_dominance", "medium",
            f"Category '{top}' is {round(100 * share)}% of the ready reserve — "
            "diversify so the feed doesn't feel samey.",
        ))
