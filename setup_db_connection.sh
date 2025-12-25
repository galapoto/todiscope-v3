#!/bin/bash
# Setup database connection for migration
# This script helps configure the database connection for the migration

set -e

echo "🔍 Checking for database setup options..."
echo ""

# Option 1: Docker Compose (if available)
if command -v docker &> /dev/null && [ -f "infra/docker-compose.yml" ]; then
    echo "✅ Docker found - Checking if database is running..."
    
    # Check if database container is running
    if docker compose -f infra/docker-compose.yml ps db 2>/dev/null | grep -q "Up"; then
        echo "✅ Database container is already running"
    else
        echo "🚀 Starting database container..."
        docker compose -f infra/docker-compose.yml up -d db
        echo "⏳ Waiting for database to be ready..."
        sleep 5
    fi
    
    export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
    echo ""
    echo "✅ Database connection configured for Docker Compose"
    echo "   Connection: postgresql+asyncpg://todiscope:***@localhost:5435/todiscope_v3"
    echo ""
    echo "You can now run:"
    echo "  python backend/migrations/execute_migration.py --verify-only"
    echo ""
    return 0
fi

# Option 2: Local PostgreSQL
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL client found"
    echo ""
    echo "Please set TODISCOPE_DATABASE_URL manually:"
    echo "  export TODISCOPE_DATABASE_URL='postgresql+asyncpg://username:password@localhost:5432/database_name'"
    echo ""
    echo "Or use direct SQL execution:"
    echo "  psql -h localhost -U username -d database_name -f backend/migrations/remove_calculation_run_parameters_column.sql"
    echo ""
    return 0
fi

# No database setup found
echo "❌ No database setup found"
echo ""
echo "Options:"
echo "  1. Install Docker and use: docker compose -f infra/docker-compose.yml up -d db"
echo "  2. Install PostgreSQL and set TODISCOPE_DATABASE_URL"
echo "  3. Use direct SQL execution with psql"
echo ""
return 1





