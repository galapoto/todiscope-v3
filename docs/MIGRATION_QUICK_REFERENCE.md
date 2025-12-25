# Migration Quick Reference

**Migration:** Remove `parameters` column from `calculation_run` table

---

## Prerequisites

✅ Virtual environment created (`.venv/`)  
✅ Dependencies installed (SQLAlchemy, asyncpg)  
⚠️ **Database connection needed**

---

## Quick Commands

### Setup Database (Docker Compose)

```bash
# 1. Install Docker (if not installed)
sudo apt install docker.io docker-compose

# 2. Start database
docker compose -f infra/docker-compose.yml up -d db

# 3. Set connection
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
```

### Run Migration

```bash
# Activate venv
source .venv/bin/activate

# Verify current state
python backend/migrations/execute_migration.py --verify-only

# Execute migration
python backend/migrations/execute_migration.py
```

### Or Use Helper Script

```bash
# Set database URL first
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'

# Run migration
./run_migration.sh --verify-only
./run_migration.sh
```

### Or Use Direct SQL

```bash
# Execute migration
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql

# Verify
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/verify_migration.sql
```

---

## Database Connection Details

**Docker Compose (from infra/docker-compose.yml):**
- Host: `localhost`
- Port: `5435`
- Database: `todiscope_v3`
- User: `todiscope`
- Password: `todiscope`
- URL: `postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3`

---

## Verification

After migration, verify:

1. **Column removed:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'calculation_run' AND column_name = 'parameters';
   -- Should return 0 rows
   ```

2. **parameter_payload exists:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'calculation_run' AND column_name = 'parameter_payload';
   -- Should return 1 row
   ```

3. **Application works:**
   ```bash
   # Start application
   source .venv/bin/activate
   uvicorn backend.app.main:app --reload
   ```

---

## Troubleshooting

**"Database not configured"**
→ Set `TODISCOPE_DATABASE_URL` environment variable

**"Connection refused"**
→ Check if database is running (`docker compose ps`)

**"Authentication failed"**
→ Verify username/password in connection string

---

**Status:** Ready to execute (once database is configured)




