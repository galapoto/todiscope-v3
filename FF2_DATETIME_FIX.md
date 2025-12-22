# FF-2 datetime.now() Remediation

## Fixes Applied

### 1. Core FX Service - Removed datetime.now()

**File:** `backend/app/core/artifacts/fx_service.py`

**Change:**
- Removed `from datetime import datetime, timezone` (removed timezone import)
- Changed `create_fx_artifact()` signature to require `created_at: datetime` parameter
- Removed `created_at=datetime.now(timezone.utc)` 
- Added validation: `created_at` must be timezone-aware

**Before:**
```python
created_at=datetime.now(timezone.utc),
```

**After:**
```python
async def create_fx_artifact(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    base_currency: str,
    effective_date: str,
    rates: dict,
    created_at: datetime,  # Required parameter
) -> FxArtifact:
    if created_at.tzinfo is None:
        raise FxArtifactError("CREATED_AT_TIMEZONE_REQUIRED: created_at must be timezone-aware")
    # ...
    row = FxArtifact(
        # ...
        created_at=created_at,  # Uses provided parameter
    )
```

---

### 2. FX API - Made created_at Required

**File:** `backend/app/core/artifacts/fx_api.py`

**Change:**
- Removed fallback `datetime.now(timezone.utc)`
- Made `created_at` required in API payload
- Returns 400 error if `created_at` not provided

**Before:**
```python
created_at_str = payload.get("created_at")
# ... fallback to datetime.now() if not provided
```

**After:**
```python
created_at_str = payload.get("created_at")
if not created_at_str:
    raise HTTPException(status_code=400, detail="CREATED_AT_REQUIRED: created_at is required for deterministic FX artifact creation")
```

---

### 3. Deterministic-Time Guard Test

**File:** `backend/tests/test_forbidden_patterns.py`

**Added:** `test_no_datetime_now_in_engines_or_artifacts()`

**Checks:**
- Scans `backend/app/engines/**` for:
  - `datetime.now(`
  - `date.today(`
  - `time.time(`
  - `datetime.utcnow(`
- Scans `backend/app/core/artifacts/**` for same patterns
- Fails if any violations found

**Purpose:** Prevents regressions of non-deterministic time usage

---

## Verification

### Core Artifacts Directory
✅ No `datetime.now()` found in `backend/app/core/artifacts/`

### Test Coverage
✅ Test `test_no_datetime_now_in_engines_or_artifacts()` will catch any future violations

---

## Remaining Issue

**Note:** Engine `run.py` still contains `datetime.now(timezone.utc)` at line 95 for `started_at` timestamp. This is a separate violation that should be addressed in engine run metadata fix (not part of this FX service fix).

---

## Status

✅ **Core FX service datetime.now() removed**
✅ **FX API requires created_at parameter**
✅ **Deterministic-time guard test added**

**FF-2 core artifacts datetime.now() violation: FIXED**


