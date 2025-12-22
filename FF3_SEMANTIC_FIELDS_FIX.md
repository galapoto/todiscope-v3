# FF-3 Semantic Fields Fix

## Fixes Applied

### 1. Finding Type Field Added

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Change:**
- Added `finding_type` field (constrained enum)
- Added check constraint: `finding_type in ('exact_match','tolerance_match','partial_match')`
- Field is indexed for query performance

**New File:** `backend/app/engines/financial_forensics/finding_type.py`
- `FindingType` enum (exact_match, tolerance_match, partial_match)
- `validate_finding_type()` function
- `derive_finding_type_from_rule_id()` function (deterministic derivation)

**Before:**
```python
# finding_type field missing
```

**After:**
```python
finding_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
# With check constraint: finding_type in ('exact_match','tolerance_match','partial_match')
```

---

### 2. Framework Version Field Added

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Change:**
- Added `framework_version` field (string, NOT NULL)
- Value locked to "financial_forensics_v1"

**New File:** `backend/app/engines/financial_forensics/framework_version.py`
- `FRAMEWORK_VERSION` constant = "financial_forensics_v1"

**Before:**
```python
# framework_version field missing
```

**After:**
```python
framework_version: Mapped[str] = mapped_column(String, nullable=False)
# Value: "financial_forensics_v1"
```

---

### 3. Primary Evidence Item ID Field Added

**File:** `backend/app/engines/financial_forensics/models/findings.py`

**Change:**
- Added `primary_evidence_item_id` field (FK to evidence_records.evidence_id)
- Field is NOT NULL and indexed
- References the main evidence bundle for this finding

**Before:**
```python
# Only evidence_ids (list) existed, no primary_evidence_item_id
evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
```

**After:**
```python
# Primary evidence item reference (mandatory, FK to evidence_records)
primary_evidence_item_id: Mapped[str] = mapped_column(
    String, ForeignKey("evidence_records.evidence_id"), nullable=False, index=True
)

# Evidence IDs (list of additional evidence_item_id references)
evidence_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
```

---

## Summary

### Fields Added

1. ✅ `finding_type` — Constrained enum (exact_match, tolerance_match, partial_match)
2. ✅ `framework_version` — String, locked to "financial_forensics_v1"
3. ✅ `primary_evidence_item_id` — FK to evidence_records.evidence_id, NOT NULL

### Constraints Added

- Check constraint for `finding_type` enum values
- FK constraint for `primary_evidence_item_id` to `evidence_records.evidence_id`
- Indexes on `finding_type` and `primary_evidence_item_id` for query performance

### New Files Created

1. `backend/app/engines/financial_forensics/finding_type.py` — Finding type enum and validation
2. `backend/app/engines/financial_forensics/framework_version.py` — Framework version constant

---

## Status

✅ **All semantic fields added to finding model**

**Remaining:** `run_id` field still needs to be added (separate task, not part of semantic fields fix)

---

**END OF FF-3 SEMANTIC FIELDS FIX**


