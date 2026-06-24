"""Guardrails — the Prime Directive, encoded.

Nothing reaches publication without passing :func:`check`. This module is the
single most important part of INVISABLE OS: it is where the values stop being a
README and become enforced behaviour.
"""

from invisable_os.guardrails.engine import check, explain
from invisable_os.guardrails.policy import (
    BANNED_EMOJI,
    NEVER_DO,
    NEVER_OPTIMISE_FOR,
    OPTIMISE_FOR,
)

__all__ = [
    "check",
    "explain",
    "BANNED_EMOJI",
    "NEVER_DO",
    "NEVER_OPTIMISE_FOR",
    "OPTIMISE_FOR",
]
