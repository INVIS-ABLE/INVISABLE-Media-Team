"""The engines of INVISABLE OS.

Each engine is a cooperating subsystem. They share one memory (``INVISABLE_BRAIN``)
and one set of values (``guardrails``), which is what makes the platform unified.

* :mod:`~invisable_os.engines.tournament`  — Content Tournament Engine
* :mod:`~invisable_os.engines.watchtower`  — Algorithm Watchtower
* :mod:`~invisable_os.engines.cultural`    — Cultural Intelligence Engine
* :mod:`~invisable_os.engines.harvester`   — Intelligence Harvester
* :mod:`~invisable_os.engines.founder`     — Founder Engine
"""

from invisable_os.engines.cultural import CulturalIntelligenceEngine
from invisable_os.engines.daily import DailyContentDirector
from invisable_os.engines.engagement import CommunityEngagement
from invisable_os.engines.flywheel import ContentFlywheel
from invisable_os.engines.founder import FounderEngine
from invisable_os.engines.harvester import IntelligenceHarvester
from invisable_os.engines.insights import detect_theme_alerts
from invisable_os.engines.mission import MissionEngine
from invisable_os.engines.quality import QualityEngine
from invisable_os.engines.remix import (
    ParodyEngine,
    PopCultureIndex,
    RemixTrendEngine,
    RightsManager,
    TrendScanner,
    VoiceoverEngine,
)
from invisable_os.engines.studio import StudioEngine
from invisable_os.engines.tagging import TagNetwork
from invisable_os.engines.tournament import ContentTournamentEngine
from invisable_os.engines.watchtower import AlgorithmWatchtower

__all__ = [
    "ContentTournamentEngine",
    "AlgorithmWatchtower",
    "CulturalIntelligenceEngine",
    "IntelligenceHarvester",
    "FounderEngine",
    "CommunityEngagement",
    "DailyContentDirector",
    "MissionEngine",
    "QualityEngine",
    "ContentFlywheel",
    "detect_theme_alerts",
    "TagNetwork",
    "RemixTrendEngine",
    "TrendScanner",
    "RightsManager",
    "PopCultureIndex",
    "ParodyEngine",
    "VoiceoverEngine",
    "StudioEngine",
]
