"""Outbound integrations — push/pull adapters to external systems.

Each integration is **graceful**: unconfigured or unreachable, it degrades to a
dry-run/empty result rather than raising, so the platform always runs offline and in
CI. Clients accept an injectable ``httpx.Client`` so they can be exercised with
``httpx.MockTransport`` without network.
"""

from invisable_os.integrations.metricool import MetricoolClient, metricool_to_signals
from invisable_os.integrations.resourcespace import ResourceSpaceClient

__all__ = ["ResourceSpaceClient", "MetricoolClient", "metricool_to_signals"]
