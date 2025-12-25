# Quick Start: Database Migration

**Current Situation:** Database connection is not configured. You need to set up a database connection before running the migration.

---

## Your Options

### Option 1: Install Docker and Use Docker Compose (Easiest) ⭐

**Install Docker:**
```bash
# Ubuntu/Debian
sudo apt install docker.io docker-compose

# Or using snap
sudo snap install docker
```

**Start Database:**
```bash
# Start PostgreSQL
docker compose -f infra/docker-compose.yml up -d db

# Wait a few seconds, then set connection
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'

# Verify connection
source .venv/bin/activate
python backend/migrations/execute_migration.py --verify-only
```

---

### Option 2: Use Existing PostgreSQL Database

If you have access to a PostgreSQL database (local or remote):

**Set Connection:**
```bash
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://username:password@host:port/database_name'
```

**Example:**
```bash
# Local PostgreSQL
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://postgres:postgres@localhost:5432/todiscope_v3'

# Remote PostgreSQL
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://user:pass@db.example.com:5432/todiscope_v3'
```

**Then run migration:**
```bash
source .venv/bin/activate
python backend/migrations/execute_migration.py
```

---

### Option 3: Direct SQL Execution (No Python Required)

If you have `psql` installed or can connect to the database:

**Install PostgreSQL Client (if needed):**
```bash
sudo apt install postgresql-client
```

**Execute Migration:**
```bash
# For Docker Compose database (once it's running)
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql

# For local PostgreSQL
psql -h localhost -U username -d database_name -f backend/migrations/remove_calculation_run_parameters_column.sql
```

**Verify Migration:**
```bash
# Check if column is dropped
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'calculation_run' AND column_name = 'parameters';"
# Should return 0 rows
```

---

## Recommended: Docker Compose Setup

**Step 1: Install Docker**
```bash
sudo apt install docker.io docker-compose
# Or: sudo snap install docker
```

**Step 2: Start Database**
```bash
docker compose -f infra/docker-compose.yml up -d db
```

**Step 3: Set Environment Variable**
```bash
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
```

**Step 4: Run Migration**
```bash
source .venv/bin/activate
python backend/migrations/execute_migration.py --verify-only  # Check current state
python backend/migrations/execute_migration.py                # Execute migration
```

---

## Quick Test (Without Database)

If you just want to test the migration script syntax:

```bash
source .venv/bin/activate
python backend/migrations/execute_migration.py --help
```

This will show the help message without requiring a database connection.

---

## Next Steps

1. **Choose your database setup method** (Docker recommended)
2. **Configure the connection** (set TODISCOPE_DATABASE_URL)
3. **Run the migration** (using Python script or direct SQL)
4. **Verify success** (check that parameters column is removed)

---

**Need Help?** See `DATABASE_SETUP_GUIDE.md` for detailed instructions.




