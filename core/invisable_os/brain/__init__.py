"""INVISABLE_BRAIN — the shared long-term memory of the platform.

Every engine reads from and writes back to the Brain. That is what makes INVISABLE
OS *one platform* rather than disconnected tools: the Watchtower's learnings about
what performed, the Harvester's signals, the Cultural engine's notes, and the
Tournament's winning patterns all accumulate here and inform future decisions.

The Brain uses ChromaDB when available and transparently falls back to an
in-process store so it is always usable in tests and local runs.
"""

from invisable_os.brain.memory import Brain, Memory, get_brain

__all__ = ["Brain", "Memory", "get_brain"]
