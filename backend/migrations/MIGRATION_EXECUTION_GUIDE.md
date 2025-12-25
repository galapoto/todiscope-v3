# Database Migration Execution Guide

**Migration:** Remove `parameters` column from `calculation_run` table  
**Date:** 2025-01-XX  
**Status:** Ready for Execution

---

## Pre-Migration Checklist

Before executing this migration, verify:

- [ ] **Backup database** - Create a full backup of the database
- [ ] **Test environment** - Execute migration in test/staging first
- [ ] **Data verification** - Verify `parameter_payload` contains all data (if any existing records)
- [ ] **Application downtime** - Plan for brief downtime if needed
- [ ] **Rollback plan** - Have rollback script ready (see below)

---

## Migration Script

**File:** `backend/migrations/remove_calculation_run_parameters_column.sql`

```sql
-- Migration: Remove duplicate 'parameters' column from calculation_run table
-- Date: 2025-01-XX
-- Description: Removes the duplicate 'parameters' column, keeping only 'parameter_payload'
--              as the single source of truth for calculation parameters.

-- Step 1: Verify that parameter_payload contains the same data as parameters
-- (This should be verified before running the migration)

-- Step 2: Drop the parameters column
ALTER TABLE calculation_run DROP COLUMN IF EXISTS parameters;
```

---

## Execution Steps

### Option 1: Direct SQL Execution (PostgreSQL)

```bash
# Connect to your database
psql -h <host> -U <user> -d <database>

# Execute migration
\i backend/migrations/remove_calculation_run_parameters_column.sql

# Or execute directly:
psql -h <host> -U <user> -d <database> -f backend/migrations/remove_calculation_run_parameters_column.sql
```

### Option 2: Using Database Client

1. Connect to your database using your preferred client (pgAdmin, DBeaver, etc.)
2. Open the migration script
3. Execute the SQL command
4. Verify the column is dropped

### Option 3: Application-Level Execution

If your application has a migration runner, execute:

```python
# Example (adjust based on your setup)
from sqlalchemy import text
from backend.app.core.db import get_db_session

async def execute_migration():
    async with get_db_session() as db:
        with open("backend/migrations/remove_calculation_run_parameters_column.sql") as f:
            migration_sql = f.read()
        await db.execute(text(migration_sql))
        await db.commit()
```

---

## Pre-Migration Data Verification

**IMPORTANT:** Before dropping the column, verify data integrity:

```sql
-- Check if any records exist
SELECT COUNT(*) FROM calculation_run;

-- Verify parameter_payload is populated (if records exist)
SELECT 
    run_id,
    CASE 
        WHEN parameter_payload IS NULL OR parameter_payload = '{}'::jsonb THEN 'EMPTY'
        ELSE 'POPULATED'
    END as payload_status,
    CASE 
        WHEN parameters IS NULL OR parameters = '{}'::jsonb THEN 'EMPTY'
        ELSE 'POPULATED'
    END as old_params_status
FROM calculation_run
LIMIT 10;

-- If parameter_payload is empty but parameters has data, copy it first:
-- UPDATE calculation_run 
-- SET parameter_payload = parameters 
-- WHERE (parameter_payload IS NULL OR parameter_payload = '{}'::jsonb) 
--   AND parameters IS NOT NULL 
--   AND parameters != '{}'::jsonb;
```

---

## Post-Migration Verification

After executing the migration, verify:

```sql
-- 1. Verify column is dropped
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'calculation_run' 
  AND column_name = 'parameters';
-- Should return 0 rows

-- 2. Verify parameter_payload column exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'calculation_run' 
  AND column_name = 'parameter_payload';
-- Should return 1 row

-- 3. Verify parameters_hash column exists
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'calculation_run' 
  AND column_name = 'parameters_hash';
-- Should return 1 row

-- 4. Test application can read CalculationRun records
SELECT run_id, parameter_payload, parameters_hash 
FROM calculation_run 
LIMIT 1;
```

---

## Rollback Script (If Needed)

If you need to rollback (add the column back):

```sql
-- Rollback: Add parameters column back
ALTER TABLE calculation_run 
ADD COLUMN parameters JSONB;

-- Copy data from parameter_payload (if needed)
UPDATE calculation_run 
SET parameters = parameter_payload 
WHERE parameters IS NULL;
```

**Note:** Only use rollback if absolutely necessary. The application code no longer uses the `parameters` field.

---

## Application Verification

After migration, verify the application:

1. **Start the application** - Ensure it starts without errors
2. **Test CalculationRun creation** - Create a test calculation run
3. **Verify data persistence** - Check that `parameter_payload` is stored correctly
4. **Verify hash computation** - Check that `parameters_hash` is computed correctly
5. **Test calculation retrieval** - Retrieve and verify calculation runs

### Test Script

```python
# Test calculation run creation
from backend.app.core.calculation import create_calculation_run
from datetime import datetime, timezone

async def test_calculation_run():
    async with get_db_session() as db:
        run = await create_calculation_run(
            db,
            dataset_version_id="test-dv-id",
            engine_id="test-engine",
            engine_version="1.0.0",
            parameter_payload={"test": "data"},
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            actor_id="test-user",
        )
        
        # Verify parameter_payload is stored
        assert run.parameter_payload == {"test": "data"}
        
        # Verify parameters_hash is computed
        assert run.parameters_hash is not None
        assert len(run.parameters_hash) == 64  # SHA256 hex length
        
        # Verify no parameters field exists (should raise AttributeError)
        try:
            _ = run.parameters
            assert False, "parameters field should not exist"
        except AttributeError:
            pass  # Expected
```

---

## Environment-Specific Instructions

### Development Environment

```bash
# Safe to execute directly
psql -h localhost -U postgres -d todiscope_dev -f backend/migrations/remove_calculation_run_parameters_column.sql
```

### Staging Environment

1. Create backup
2. Execute migration during maintenance window
3. Verify application functionality
4. Monitor for 24 hours

### Production Environment

1. **Schedule maintenance window**
2. **Create full database backup**
3. **Execute migration during low-traffic period**
4. **Verify immediately after execution**
5. **Monitor application logs for errors**
6. **Have rollback plan ready**

---

## Troubleshooting

### Issue: Column doesn't exist

**Error:** `column "parameters" does not exist`

**Solution:** This is fine - the migration uses `DROP COLUMN IF EXISTS`, so it's safe to run even if the column doesn't exist.

### Issue: Foreign key constraints

**Error:** Cannot drop column due to constraints

**Solution:** This shouldn't happen for the `parameters` column, but if it does, check for any views or functions referencing it.

### Issue: Application errors after migration

**Error:** Application fails to start or errors when accessing CalculationRun

**Solution:**
1. Check application logs
2. Verify SQLAlchemy models match database schema
3. Clear any cached model definitions
4. Restart application

---

## Success Criteria

Migration is successful when:

- [ ] `parameters` column is dropped from `calculation_run` table
- [ ] `parameter_payload` column exists and is populated
- [ ] `parameters_hash` column exists and is populated
- [ ] Application starts without errors
- [ ] CalculationRun creation works correctly
- [ ] CalculationRun retrieval works correctly
- [ ] No references to `parameters` field in application code

---

## Next Steps After Migration

Once migration is complete:

1. ✅ **Verify application functionality**
2. ✅ **Update deployment documentation**
3. ✅ **Proceed with Financial Forensics Engine integration**
4. ✅ **Monitor application for 24-48 hours**

---

**Migration Status:** Ready for Execution  
**Risk Level:** Low (column is duplicate, data preserved in `parameter_payload`)  
**Estimated Downtime:** < 1 minute (if any)





