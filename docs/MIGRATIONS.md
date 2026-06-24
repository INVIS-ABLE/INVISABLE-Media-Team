# Database migrations & production hardening

## Two ways the schema gets created

| Mode | How tables are made | When |
| ---- | ------------------- | ---- |
| **Dev / SQLite** (default) | `create_all` on boot (`init_db`) | Zero-config — the app just runs |
| **Production / Postgres** | `alembic upgrade head` | Run once against a fresh database, then on each deploy |

Both derive from the same ORM metadata, so they produce the same schema. Use Alembic
in production so schema changes are **versioned and reversible** rather than relying
on `create_all` (which can't evolve an existing table).

## Running migrations

From `core/` (URL resolved exactly like the app: `DATABASE_URL`, else the local
SQLite file):

```bash
pip install -e ".[migrations,postgres]"

export DATABASE_URL=postgresql+psycopg://invisable:invisable@postgres:5432/invisable
alembic upgrade head      # provision / migrate
alembic current           # show the applied revision
alembic downgrade -1      # roll back one revision
```

The Docker image ships `alembic.ini` + `migrations/` and installs the `migrations`
extra, so `alembic upgrade head` is available in the container.

## Adding a schema change

1. Edit the ORM models in `invisable_os/store/models.py`.
2. Autogenerate a revision against a database at the current head:
   ```bash
   alembic revision --autogenerate -m "add X"
   ```
3. Review the generated file in `migrations/versions/`, then `alembic upgrade head`.

`0001_baseline` is a squash baseline that builds the entire current schema from the
metadata; new revisions stack on top of it.

## CI coverage (production hardening)

`.github/workflows/ci.yml` runs three jobs:

- **test** — lint + full suite on SQLite.
- **test-postgres** — spins up a `postgres:16` service and runs
  `tests/test_postgres_store.py` (repository round-trip on real Postgres) **and**
  `alembic upgrade head` against it, so the SQL path and migrations are proven on
  Postgres, not just SQLite.
- **docker-build** — builds the core image so Dockerfile/dependency breakage fails
  CI instead of a deploy.
