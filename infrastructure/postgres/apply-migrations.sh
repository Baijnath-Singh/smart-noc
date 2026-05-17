#!/bin/bash
# Apply PostgreSQL migrations to existing Smart NOC database
# Usage: ./apply-migrations.sh [migration_file]

set -e

CONTAINER="smart-noc-postgres"
USER="noc_admin"
DB="smart_noc"
MIGRATIONS_DIR="infrastructure/postgres/migrations"

echo "🔧 Smart NOC - Database Migration Tool"
echo "========================================"

# Check if postgres container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "❌ Error: PostgreSQL container '${CONTAINER}' is not running"
    echo "   Start it with: docker compose up -d postgres"
    exit 1
fi

# Function to apply a single migration
apply_migration() {
    local migration_file=$1
    local migration_name=$(basename "$migration_file")
    
    echo ""
    echo "📝 Applying: $migration_name"
    
    if docker compose exec -T postgres psql -U "$USER" -d "$DB" < "$migration_file"; then
        echo "✅ Successfully applied: $migration_name"
        return 0
    else
        echo "❌ Failed to apply: $migration_name"
        return 1
    fi
}

# If specific migration file provided
if [ -n "$1" ]; then
    if [ -f "$1" ]; then
        apply_migration "$1"
    else
        echo "❌ Error: Migration file '$1' not found"
        exit 1
    fi
else
    # Apply all migrations in order
    echo ""
    echo "🔍 Found migrations:"
    ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null || {
        echo "❌ No migration files found in $MIGRATIONS_DIR"
        exit 1
    }
    
    echo ""
    echo "📦 Applying all migrations in order..."
    
    for migration in "$MIGRATIONS_DIR"/*.sql; do
        apply_migration "$migration" || exit 1
    done
    
    echo ""
    echo "🎉 All migrations applied successfully!"
fi

# Verify tables exist
echo ""
echo "📊 Current database schema:"
docker compose exec postgres psql -U "$USER" -d "$DB" -c "\dt" | grep -E "incidents|remediation|diagnosis" || true

echo ""
echo "✅ Migration complete!"
