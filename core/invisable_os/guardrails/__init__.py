"""Guardrails — the Prime Directive, encoded.

Nothing reaches publication without passing :func:`check`. This module is the
single most important part of INVISABLE OS: it is where the values stop being a
README and become enforced behaviour.
"""

from invisable_os.guardrails.crisis import (
    CrisisVerdict,
    SensitiveTopic,
    crisis_review,
    detect_sensitive_topics,
)
from invisable_os.guardrails.engine import (
    check,
    explain,
    humour_violations,
    risk_scan,
    swear_level,
)
from invisable_os.guardrails.policy import (
    BANNED_EMOJI,
    NEVER_DO,
    NEVER_OPTIMISE_FOR,
    OPTIMISE_FOR,
    RISK_CATEGORIES,
)
from invisable_os.guardrails.rights import (
    RIGHTS_RULE,
    RightsVerdict,
    can_download,
    can_reuse,
    filter_usable,
    reuse_check,
)

__all__ = [
    "check",
    "explain",
    "humour_violations",
    "risk_scan",
    "swear_level",
    "crisis_review",
    "detect_sensitive_topics",
    "CrisisVerdict",
    "SensitiveTopic",
    "BANNED_EMOJI",
    "NEVER_DO",
    "NEVER_OPTIMISE_FOR",
    "OPTIMISE_FOR",
    "RISK_CATEGORIES",
    "RIGHTS_RULE",
    "RightsVerdict",
    "can_download",
    "can_reuse",
    "filter_usable",
    "reuse_check",
]
