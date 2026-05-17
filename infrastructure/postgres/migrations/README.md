# PostgreSQL Migrations

This directory contains database schema migrations that run automatically when PostgreSQL starts for the first time.

## 📁 Migration Files

Migrations run in **alphabetical order**:

1. `002_add_diagnosis_columns.sql` - Phase 4: LLM diagnosis tables
2. `003_add_remediation_tables.sql` - Phase 5: Autonomous remediation tables

## 🚀 For New Installations

Migrations run automatically via `docker-entrypoint-initdb.d/`:
```bash
docker compose up postgres
```

All schema changes are applied automatically.

## 🔧 For Existing Databases

If you already have a running database, apply migrations manually:

```bash
# Apply single migration
docker compose exec postgres psql -U noc_admin -d smart_noc \
  -f /docker-entrypoint-initdb.d/migrations/003_add_remediation_tables.sql

# Apply all migrations
docker compose exec postgres bash -c \
  'for f in /docker-entrypoint-initdb.d/migrations/*.sql; do
     psql -U noc_admin -d smart_noc -f "$f"
   done'
```

### Alternative: From Host Machine

```bash
# Windows PowerShell
docker compose exec -T postgres psql -U noc_admin -d smart_noc < infrastructure/postgres/migrations/003_add_remediation_tables.sql

# Linux/Mac
docker compose exec -T postgres psql -U noc_admin -d smart_noc < infrastructure/postgres/migrations/003_add_remediation_tables.sql
```

## ✅ Verify Migration Applied

```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c "\d remediation_executions"
docker compose exec postgres psql -U noc_admin -d smart_noc -c "\d remediation_stats"
```

## 📝 Creating New Migrations

1. **Name with sequence**: `00X_descriptive_name.sql`
2. **Use idempotent SQL**: `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`
3. **Test locally** before committing
4. **Document changes** in comments

Example:
```sql
-- Migration: 004_add_notifications.sql
-- Purpose: Add notification system tables

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    ...
);
```

## 🔄 Migration Execution Order

1. `001_init.sql` (base schema: incidents, anomalies, timeline)
2. `002_add_diagnosis_columns.sql` (diagnosis tables and views)
3. `003_add_remediation_tables.sql` (remediation tables and views)

PostgreSQL's `docker-entrypoint-initdb.d` runs files in lexicographic order.

## ⚠️ Important Notes

- Migrations only run on **first container startup** (empty database)
- For existing databases, apply migrations manually
- Always use `IF NOT EXISTS` to make migrations rerunnable
- Never delete old migrations - they're part of schema history
