"""Selects the active publisher: Postiz when configured, else safe dry-run."""

from __future__ import annotations

from invisable_os.publish.base import DryRunPublisher, Publisher
from invisable_os.publish.postiz import PostizPublisher


def get_publisher() -> Publisher:
    postiz = PostizPublisher()
    if postiz.configured:
        return postiz
    return DryRunPublisher()
