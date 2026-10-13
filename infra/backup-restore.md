# Backup & restore — Cureva Care database

PostgreSQL is the system of record. Source files (register photos) live in
object storage (MinIO/S3) and are immutable; back those up with the object
store's own replication/versioning.

## Backup (logical dump)

```bash
docker exec cureva-postgres pg_dump -U cureva -d cureva -f /tmp/cureva_backup.sql
docker cp cureva-postgres:/tmp/cureva_backup.sql ./cureva_backup_$(date +%F).sql
```

For production, schedule `pg_dump` (or use managed-Postgres point-in-time
recovery) and ship the dump off-host to encrypted storage.

## Restore

```bash
# into a fresh database (never overwrite the live one without a drill)
docker exec cureva-postgres psql -U cureva -d postgres -c "CREATE DATABASE cureva_restore;"
docker exec cureva-postgres psql -U cureva -d cureva_restore -f /tmp/cureva_backup.sql
```

## Restore drill (verified 2026-10-13)

A restore drill was performed before launch readiness: a logical dump was
restored into a throwaway database with **0 errors**, and row counts were
verified intact (states, wards, platform settings, templates). The temp
database was dropped afterwards. Re-run this drill before accepting live
maternal data, and after any major schema migration.

## Incident response (tabletop)

Before live data: run a tabletop covering (1) a lost DB host — restore from the
latest dump to a new host, repoint `DATABASE_URL`; (2) a leaked credential —
rotate the env secret and redeploy (secrets are never in `platform_settings`
or source); (3) a bad publish — source rows are append-only and raw values are
never overwritten, so re-projection is idempotent. Record owners and timings.
