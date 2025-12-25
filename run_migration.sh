#!/bin/bash
# Quick migration runner script
# This script helps you run the migration with proper setup

set -e

echo "🚀 TodiScope v3 Migration Runner"
echo "================================"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated"
    echo "   Activating .venv..."
    source .venv/bin/activate
fi

# Check for database URL
if [ -z "$TODISCOPE_DATABASE_URL" ]; then
    echo "⚠️  TODISCOPE_DATABASE_URL not set"
    echo ""
    echo "Options:"
    echo ""
    echo "1. Use Docker Compose (recommended):"
    echo "   docker compose -f infra/docker-compose.yml up -d db"
    echo "   export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'"
    echo ""
    echo "2. Set manually:"
    echo "   export TODISCOPE_DATABASE_URL='postgresql+asyncpg://user:password@host:port/database'"
    echo ""
    echo "3. Use direct SQL (no Python needed):"
    echo "   PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql"
    echo ""
    exit 1
fi

echo "✅ Database URL configured"
echo ""

# Run migration script with provided arguments
python backend/migrations/execute_migration.py "$@"





