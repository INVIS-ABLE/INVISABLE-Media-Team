"""baseline — the full current operational schema

Squash baseline: from an empty database, ``alembic upgrade head`` provisions every
table the app owns (derived from the ORM metadata, so it can never drift from the
models). Subsequent schema changes get their own revisions on top of this one.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-25 00:00:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    from invisable_os.store import models  # noqa: F401 — registers the mappers
    from invisable_os.store.db import Base

    Base.metadata.create_all(op.get_bind())


def downgrade() -> None:
    from invisable_os.store import models  # noqa: F401
    from invisable_os.store.db import Base

    Base.metadata.drop_all(op.get_bind())
