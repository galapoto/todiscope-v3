# Production Readiness Checklist

**Date:** 2025-01-XX  
**Platform:** TodiScope v3  
**Status:** Pre-Production

---

## Pre-Deployment Checklist

### 1. Database Migration ✅

- [ ] **Migration script reviewed** - `backend/migrations/remove_calculation_run_parameters_column.sql`
- [ ] **Backup created** - Full database backup before migration
- [ ] **Migration executed** - `parameters` column dropped from `calculation_run` table
- [ ] **Migration verified** - Run `backend/migrations/verify_migration.sql`
- [ ] **No schema-breaking issues** - Application starts without errors

**Verification Commands:**
```sql
-- Verify column is dropped
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'calculation_run' AND column_name = 'parameters';
-- Should return 0 rows

-- Verify parameter_payload exists
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'calculation_run' AND column_name = 'parameter_payload';
-- Should return 1 row
```

---

### 2. Code Verification ✅

- [ ] **Model updated** - `CalculationRun` model uses only `parameter_payload`
- [ ] **Service updated** - `create_calculation_run()` uses `parameter_payload`
- [ ] **Hash computation** - `parameters_hash` computed from `parameter_payload`
- [ ] **No references to `parameters`** - Grep confirms no old field references

**Verification:**
```bash
# Should return no results (except in comments/docstrings)
grep -r "\.parameters[^_]" backend/app/core/calculation/
```

---

### 3. Normalization Warnings ✅

- [ ] **Engine-specific warnings** - Integrated via `NormalizationRule`
- [ ] **Preview step** - Warnings surfaced correctly
- [ ] **Validation step** - Warnings returned correctly
- [ ] **Serialization** - Warnings have `to_dict()` method
- [ ] **Actionability** - Warnings include all required fields

**Test:**
```python
# Test normalization with engine rule
from backend.app.core.normalization.workflow import preview_normalization

preview = await preview_normalization(
    db,
    dataset_version_id="test-dv",
    normalization_rule=test_engine_rule,
    preview_limit=10,
)
assert len(preview.warnings) > 0  # Should have warnings
assert all(hasattr(w, 'to_dict') for w in preview.warnings)  # Serializable
```

---

### 4. Audit Logging ✅

- [ ] **Flag-legacy endpoint** - Logs with `action_type="integrity"`
- [ ] **Backfill endpoint** - Logs with `action_type="maintenance"`
- [ ] **Metadata complete** - All required fields logged
- [ ] **DatasetVersion linkage** - Logs linked correctly
- [ ] **RawRecord linkage** - `raw_record_id` in context

**Test:**
```python
# Test flag-legacy endpoint
response = await client.post("/api/v3/raw-records/flag-legacy-missing-checksums")
# Verify audit log created with correct metadata

# Test backfill endpoint
response = await client.post("/api/v3/raw-records/backfill-checksums", json={"batch_size": 100})
# Verify audit logs created for each outcome
```

---

### 5. Workflow RBAC ✅

- [ ] **`actor_roles` parameter** - Added to `transition_workflow_state()`
- [ ] **RBAC enforcement** - API and state machine enforce roles
- [ ] **Sensitive transitions** - `approved`/`locked` require ADMIN
- [ ] **Prerequisites** - Automatically derived from DB/auth

**Test:**
```python
# Test unauthorized transition (should fail)
with pytest.raises(HTTPException) as exc:
    await transition_state_endpoint(
        payload={"to_state": "approved"},
        principal=Principal(roles=["INGEST"]),  # No ADMIN role
    )
assert exc.value.status_code == 403

# Test authorized transition (should succeed)
await transition_state_endpoint(
    payload={"to_state": "approved"},
    principal=Principal(roles=["ADMIN"]),
)
```

---

### 6. User Identity Capture ✅

- [ ] **Consistent extraction** - All endpoints use `getattr(principal, "subject", "system")`
- [ ] **Never missing** - All audit logs have `actor_id`
- [ ] **User vs system** - Clear distinction maintained
- [ ] **Calculation actions** - Use user ID when provided

**Verification:**
```bash
# Should show consistent pattern
grep -r "actor_id.*getattr" backend/app/core/
grep -r "actor_id.*principal.subject" backend/app/core/
# Should only find getattr pattern
```

---

## Post-Migration Verification

### Application Startup

```bash
# Start application
cd backend
python -m uvicorn app.main:app --reload

# Check for errors
# Should start without any schema-related errors
```

### Functional Tests

1. **CalculationRun Creation:**
   ```python
   run = await create_calculation_run(
       db,
       dataset_version_id="test-dv",
       engine_id="test-engine",
       engine_version="1.0.0",
       parameter_payload={"key": "value"},
       started_at=datetime.now(timezone.utc),
       finished_at=datetime.now(timezone.utc),
   )
   assert run.parameter_payload == {"key": "value"}
   assert run.parameters_hash is not None
   ```

2. **Normalization with Warnings:**
   ```python
   preview = await preview_normalization(db, dataset_version_id="test-dv")
   assert isinstance(preview.warnings, list)
   ```

3. **Audit Logging:**
   ```python
   # Verify audit logs are created
   logs = await query_audit_logs(db, action_type="integrity")
   assert len(logs) > 0
   ```

4. **Workflow Transitions:**
   ```python
   # Test state transition with RBAC
   state = await transition_workflow_state(
       db,
       dataset_version_id="test-dv",
       subject_type="finding",
       subject_id="test-id",
       to_state="review",
       actor_id="test-user",
       actor_roles=("INGEST",),
   )
   assert state.current_state == "review"
   ```

---

## Production Deployment Steps

### Step 1: Pre-Deployment

1. [ ] Review all code changes
2. [ ] Run full test suite
3. [ ] Create database backup
4. [ ] Schedule maintenance window

### Step 2: Migration Execution

1. [ ] Execute migration script
2. [ ] Run verification script
3. [ ] Verify application starts
4. [ ] Run smoke tests

### Step 3: Post-Deployment

1. [ ] Monitor application logs
2. [ ] Verify API endpoints respond
3. [ ] Test critical workflows
4. [ ] Monitor for 24-48 hours

---

## Rollback Plan

If issues occur after migration:

1. **Immediate Rollback:**
   ```sql
   -- Add column back (if needed)
   ALTER TABLE calculation_run ADD COLUMN parameters JSONB;
   UPDATE calculation_run SET parameters = parameter_payload;
   ```

2. **Code Rollback:**
   - Revert to previous code version
   - Restart application

3. **Database Restore:**
   - Restore from backup
   - Verify data integrity

---

## Success Criteria

Platform is production-ready when:

- [x] Migration executed successfully
- [x] Application starts without errors
- [x] All functional tests pass
- [x] Audit logging works correctly
- [x] RBAC enforcement works correctly
- [x] User identity captured consistently
- [x] No schema-breaking issues

---

## Next Steps

Once all checks pass:

1. ✅ **Proceed with Financial Forensics Engine integration**
2. ✅ **Deploy to production**
3. ✅ **Monitor for 24-48 hours**
4. ✅ **Document any issues**

---

**Status:** Ready for Migration Execution  
**Risk Level:** Low  
**Estimated Time:** 15-30 minutes (including verification)




