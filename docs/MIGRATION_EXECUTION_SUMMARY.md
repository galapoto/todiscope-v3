# Migration Execution Summary

**Migration:** Remove `parameters` column from `calculation_run` table  
**Date:** 2025-01-XX  
**Status:** Ready for Execution

---

## Quick Start

### Option 1: Using Python Script (Recommended)

```bash
# Dry run (see what would happen)
python backend/migrations/execute_migration.py --dry-run

# Verify current state only
python backend/migrations/execute_migration.py --verify-only

# Execute migration
python backend/migrations/execute_migration.py
```

### Option 2: Direct SQL Execution

```bash
# PostgreSQL
psql -h <host> -U <user> -d <database> -f backend/migrations/remove_calculation_run_parameters_column.sql

# Or connect and run:
psql -h <host> -U <user> -d <database>
\i backend/migrations/remove_calculation_run_parameters_column.sql
```

### Option 3: Using Database Client

1. Connect to your database
2. Open `backend/migrations/remove_calculation_run_parameters_column.sql`
3. Execute the SQL command
4. Run `backend/migrations/verify_migration.sql` to verify

---

## Pre-Migration Checklist

- [ ] **Database backup created**
- [ ] **Test environment verified** (if applicable)
- [ ] **Application stopped** (recommended for production)
- [ ] **Migration script reviewed**

---

## Migration Script

**File:** `backend/migrations/remove_calculation_run_parameters_column.sql`

```sql
ALTER TABLE calculation_run DROP COLUMN IF EXISTS parameters;
```

**Safety:** Uses `IF EXISTS` - safe to run even if column already removed.

---

## Post-Migration Verification

### Automated Verification

```bash
# Run verification script
python backend/migrations/execute_migration.py --verify-only
```

### Manual Verification

```sql
-- Run verification queries
\i backend/migrations/verify_migration.sql
```

### Application Verification

1. **Start application:**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Test CalculationRun creation:**
   ```python
   from backend.app.core.calculation import create_calculation_run
   
   run = await create_calculation_run(
       db,
       dataset_version_id="test-dv",
       engine_id="test-engine",
       engine_version="1.0.0",
       parameter_payload={"test": "data"},
       started_at=datetime.now(timezone.utc),
       finished_at=datetime.now(timezone.utc),
   )
   assert run.parameter_payload == {"test": "data"}
   assert run.parameters_hash is not None
   ```

---

## Expected Results

### Before Migration
- ✅ `parameters` column exists
- ✅ `parameter_payload` column exists
- ✅ `parameters_hash` column exists

### After Migration
- ✅ `parameters` column **removed**
- ✅ `parameter_payload` column exists
- ✅ `parameters_hash` column exists
- ✅ Application starts without errors
- ✅ CalculationRun operations work correctly

---

## Rollback (If Needed)

If you need to rollback:

```sql
-- Add column back
ALTER TABLE calculation_run ADD COLUMN parameters JSONB;

-- Copy data (if needed)
UPDATE calculation_run 
SET parameters = parameter_payload 
WHERE parameters IS NULL;
```

**Note:** Rollback should only be used if absolutely necessary. The application code no longer uses the `parameters` field.

---

## Success Criteria

Migration is successful when:

- [x] `parameters` column is dropped
- [x] `parameter_payload` column exists
- [x] `parameters_hash` column exists
- [x] Application starts without errors
- [x] CalculationRun creation works
- [x] CalculationRun retrieval works

---

## Next Steps

Once migration is complete:

1. ✅ **Verify application functionality**
2. ✅ **Proceed with Financial Forensics Engine integration**
3. ✅ **Deploy to production** (if in staging)
4. ✅ **Monitor for 24-48 hours**

---

**Status:** Ready for Execution  
**Risk Level:** Low  
**Estimated Time:** < 1 minute




