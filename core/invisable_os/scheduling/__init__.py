"""Scheduling — the posting-slot queue and calendar.

The signature feature of every mature scheduler (Buffer, Postiz, Mixpost): define a
weekly set of posting slots per channel once, then "fill the next free slot"
automatically. This is what makes the brand *consistent* without anyone choosing a
time for every post. Architecture is borrowed from those tools (see
``docs/REFERENCES.md``); the implementation here is original.
"""

from invisable_os.scheduling.defaults import default_week
from invisable_os.scheduling.engine import calendar_by_day, next_open_slot

__all__ = ["next_open_slot", "calendar_by_day", "default_week"]
