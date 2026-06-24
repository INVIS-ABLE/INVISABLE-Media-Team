"""Metrics sync service — feed real platform performance into the Watchtower.

Pulls metrics from Metricool (or accepts signals directly), ingests them through the
Algorithm Watchtower (updating learnings + the Founder Recognition Index), and
persists each signal. Offline / unconfigured it is a safe no-op.
"""

from __future__ import annotations

from invisable_os.engines import AlgorithmWatchtower
from invisable_os.integrations import MetricoolClient, metricool_to_signals
from invisable_os.models.metrics import PerformanceSignal
from invisable_os.store import Repository, get_repository


def sync_metrics(
    *,
    signals: list[PerformanceSignal] | None = None,
    start: str = "",
    end: str = "",
    repository: Repository | None = None,
    client: MetricoolClient | None = None,
    watchtower: AlgorithmWatchtower | None = None,
) -> dict:
    """Ingest performance signals (from Metricool unless provided) and learn."""
    repo = repository or get_repository()
    source = "provided"
    if signals is None:
        mc = client or MetricoolClient()
        source = "metricool" if mc.configured else "none"
        signals = metricool_to_signals(mc.fetch(start=start, end=end))

    report = (watchtower or AlgorithmWatchtower()).ingest(signals)
    for s in signals:
        repo.record_signal(s.candidate_id, s.platform, s.metric.value, s.value, s.themes)

    return {
        "source": source,
        "ingested": len(signals),
        "totals": report.totals,
        "founder_recognition_index": report.founder_recognition_index,
        "learnings": report.learnings,
    }
