#!/bin/bash
# Complete migration runner - handles all setup steps
# Run this from the project root directory

set -e

echo "🚀 TodiScope v3 Migration Runner"
echo "================================"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/migrations/execute_migration.py" ]; then
    echo "❌ Error: Must run from project root directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected: /home/vitus-idi/Documents/todiscope-v3"
    echo ""
    echo "Please run: cd /home/vitus-idi/Documents/todiscope-v3"
    exit 1
fi

# Check Docker
if command -v docker &> /dev/null; then
    # Check if user can run docker without sudo
    if docker ps &> /dev/null; then
        DOCKER_CMD="docker-compose"
        echo "✅ Docker accessible"
    else
        DOCKER_CMD="sudo docker-compose"
        echo "⚠️  Docker requires sudo"
    fi
else
    echo "❌ Docker not found"
    exit 1
fi

# Start database
echo ""
echo "📦 Starting database..."
$DOCKER_CMD -f infra/docker-compose.yml up -d db

echo "⏳ Waiting for database to be ready..."
sleep 5

# Check if database is running
if $DOCKER_CMD -f infra/docker-compose.yml ps db | grep -q "Up"; then
    echo "✅ Database is running"
else
    echo "❌ Database failed to start"
    echo "   Check: $DOCKER_CMD -f infra/docker-compose.yml ps db"
    exit 1
fi

# Set database URL
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
echo "✅ Database URL configured"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "⚠️  Virtual environment not found (.venv/)"
    echo "   Creating it..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install sqlalchemy[asyncio] asyncpg
fi

# Run migration
echo ""
echo "🔄 Running migration..."
echo ""

python backend/migrations/execute_migration.py "$@"





