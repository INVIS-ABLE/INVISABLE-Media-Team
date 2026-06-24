"""Human-led operating layer for INVISABLE Media Studio.

The co-pilot runs alongside Stephen, never instead of him. This package holds the
posting/interaction intensity modes, the live operating state with its emergency
controls, and the Interaction Centre where the AI drafts and Stephen sends.
"""

from invisable_os.operating.interaction import (
    InteractionCentre,
    InteractionItem,
    InteractionKind,
    InteractionStatus,
    get_interaction_centre,
)
from invisable_os.operating.modes import (
    COMMENT_STYLE_RULES,
    GLOBAL_HUMAN_RULES,
    MODE_POLICIES,
    ModePolicy,
    OperatingMode,
    get_policy,
)
from invisable_os.operating.state import (
    clear_today_queue,
    founder_override,
    get_state,
    set_control,
    set_mode,
    today_status,
)

__all__ = [
    "OperatingMode",
    "ModePolicy",
    "MODE_POLICIES",
    "get_policy",
    "GLOBAL_HUMAN_RULES",
    "COMMENT_STYLE_RULES",
    "InteractionCentre",
    "InteractionItem",
    "InteractionKind",
    "InteractionStatus",
    "get_interaction_centre",
    "get_state",
    "set_mode",
    "set_control",
    "founder_override",
    "clear_today_queue",
    "today_status",
]
