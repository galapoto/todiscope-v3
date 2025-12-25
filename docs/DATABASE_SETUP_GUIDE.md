# Database Setup Guide for Migration

**Date:** 2025-01-XX  
**Purpose:** Configure database connection for migration execution

---

## Database Configuration Options

### Option 1: Use Docker Compose (Recommended)

If you have Docker installed, start the database:

```bash
# Start PostgreSQL and MinIO
docker compose -f infra/docker-compose.yml up -d db

# Wait for database to be ready
docker compose -f infra/docker-compose.yml ps db
```

**Connection Details (from docker-compose.yml):**
- **Host:** localhost
- **Port:** 5435 (mapped from container port 5432)
- **Database:** todiscope_v3
- **User:** todiscope
- **Password:** todiscope

**Set Environment Variable:**
```bash
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
```

---

### Option 2: Use Local PostgreSQL

If you have PostgreSQL installed locally:

**Check if PostgreSQL is running:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Or check if port is open
pg_isready -h localhost -p 5432
```

**Set Environment Variable:**
```bash
# Adjust credentials and database name as needed
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://username:password@localhost:5432/database_name'
```

---

### Option 3: Use Direct SQL (No Python Required)

If you have `psql` installed, you can execute the migration directly:

**For Docker Compose Database:**
```bash
# Connect to database
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3

# Or in one command:
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql
```

**For Local PostgreSQL:**
```bash
# Connect to database
psql -h localhost -U username -d database_name

# Or execute migration directly:
psql -h localhost -U username -d database_name -f backend/migrations/remove_calculation_run_parameters_column.sql
```

---

## Quick Setup Script

Create a helper script to set up the database connection:

```bash
# Create setup script
cat > setup_db_connection.sh << 'EOF'
#!/bin/bash
# Setup database connection for migration

# Option 1: Docker Compose (if available)
if command -v docker &> /dev/null; then
    echo "Starting Docker Compose database..."
    docker compose -f infra/docker-compose.yml up -d db
    sleep 5  # Wait for database to be ready
    
    export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
    echo "✅ Database connection configured for Docker Compose"
    echo "   Connection: postgresql+asyncpg://todiscope:***@localhost:5435/todiscope_v3"
    return 0
fi

# Option 2: Local PostgreSQL
if command -v psql &> /dev/null; then
    echo "Using local PostgreSQL..."
    # Adjust these values as needed
    export TODISCOPE_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/todiscope_v3'
    echo "✅ Database connection configured for local PostgreSQL"
    echo "   Please adjust TODISCOPE_DATABASE_URL if needed"
    return 0
fi

echo "❌ No database setup found"
echo "   Please install Docker or PostgreSQL, or set TODISCOPE_DATABASE_URL manually"
return 1
EOF

chmod +x setup_db_connection.sh
```

**Usage:**
```bash
source setup_db_connection.sh
python backend/migrations/execute_migration.py --verify-only
```

---

## Verification Steps

### 1. Check Database Connection

**Using Python script:**
```bash
source .venv/bin/activate
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
python backend/migrations/execute_migration.py --verify-only
```

**Using psql:**
```bash
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -c "SELECT version();"
```

### 2. Execute Migration

**Using Python script:**
```bash
source .venv/bin/activate
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
python backend/migrations/execute_migration.py
```

**Using psql:**
```bash
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql
```

### 3. Verify Migration

**Using Python script:**
```bash
python backend/migrations/execute_migration.py --verify-only
```

**Using psql:**
```bash
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/verify_migration.sql
```

---

## Troubleshooting

### Issue: "Database not configured"

**Solution:** Set the `TODISCOPE_DATABASE_URL` environment variable:
```bash
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://user:password@host:port/database'
```

### Issue: "Connection refused"

**Solution:** 
1. Check if database is running
2. Verify host and port are correct
3. Check firewall settings

### Issue: "Authentication failed"

**Solution:**
1. Verify username and password
2. Check PostgreSQL authentication settings
3. Ensure user has access to the database

---

## Recommended Approach

**For Development:**
1. Use Docker Compose (easiest setup)
2. Set environment variable
3. Run Python migration script

**For Production:**
1. Use direct SQL execution (more control)
2. Verify with SQL queries
3. Test application after migration

---

**Next Steps:**
1. Choose your database setup method
2. Configure connection
3. Execute migration
4. Verify success




