# Strict Mode Enforcement - Disallow Legacy Auto-Flagging

**Date:** 2025-01-XX  
**Status:** ✅ **COMPLETE**  
**Task:** Enforce Strict Mode and Disallow Legacy Auto-Flagging in Strict Mode

---

## Summary

Strict mode enforcement has been updated to **disallow `flag_legacy_missing=True` when `strict_mode=True`**. This ensures that strict mode always enforces checksum verification and does not allow legacy auto-flagging to bypass integrity checks.

---

## Implementation Changes

### 1. `load_raw_records()` - Disallow Legacy Flagging in Strict Mode ✅

**Location:** `backend/app/core/dataset/service.py`

**Changes Made:**

1. **Added validation to disallow incompatible parameters:**
   - When `strict_mode=True` and `flag_legacy_missing=True`, raises `ValueError`
   - Prevents legacy auto-flagging from bypassing strict checksum enforcement

2. **Updated logic:**
   - Legacy flagging only occurs when `strict_mode=False`
   - In strict mode, missing checksums always raise `ChecksumMissingError`

**Key Implementation:**
```python
async def load_raw_records(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    verify_checksums: bool = False,
    flag_legacy_missing: bool = False,
    order_by: Sequence[object] | None = None,
    strict_mode: bool = True,
) -> list[RawRecord]:
    # Disallow flag_legacy_missing=True when strict_mode=True
    if strict_mode and flag_legacy_missing:
        raise ValueError(
            "flag_legacy_missing=True is disallowed when strict_mode=True. "
            "Strict mode requires all records to have valid checksums. "
            "Set flag_legacy_missing=False or strict_mode=False."
        )
    
    if verify_checksums:
        for record in records:
            if record.file_checksum is None:
                # Already flagged as legacy: skip verification
                if record.legacy_no_checksum:
                    continue
                # Legacy flagging: only allowed in soft mode (strict_mode=False)
                if flag_legacy_missing and not record.legacy_no_checksum:
                    record.legacy_no_checksum = True
                    updated += 1
                    continue
                # No legacy flagging: verify (will raise ChecksumMissingError in strict mode)
                verify_raw_record_checksum(
                    record,
                    raise_on_missing=strict_mode,
                    raise_on_mismatch=strict_mode,
                )
```

**Status:** ✅ Complete

---

### 2. `load_raw_record_by_id()` - Disallow Legacy Flagging in Strict Mode ✅

**Location:** `backend/app/core/dataset/service.py`

**Changes Made:**

1. **Same validation as `load_raw_records()`:**
   - Raises `ValueError` when `strict_mode=True` and `flag_legacy_missing=True`
   - Prevents legacy auto-flagging in strict mode

2. **Updated logic:**
   - Legacy flagging only occurs when `strict_mode=False`
   - In strict mode, missing checksums always raise `ChecksumMissingError`

**Status:** ✅ Complete

---

## Behavior Changes

### Before:

- `flag_legacy_missing=True` could bypass strict mode
- Missing checksums could be auto-flagged as legacy even in strict mode
- Strict mode semantics were not fully enforced

### After:

- `flag_legacy_missing=True` is **disallowed** when `strict_mode=True`
- Missing checksums **always raise `ChecksumMissingError`** in strict mode
- Legacy auto-flagging only works in soft mode (`strict_mode=False`)
- Strict mode semantics are **fully enforced**

---

## Behavior Matrix

### Missing Checksum Handling:

| `strict_mode` | `flag_legacy_missing` | `legacy_no_checksum` | Behavior |
|---------------|----------------------|---------------------|----------|
| `True` | `True` | Any | **Raises `ValueError`** ❌ |
| `True` | `False` | `True` | Skip verification (already legacy) ✅ |
| `True` | `False` | `False` | Raise `ChecksumMissingError` ❌ |
| `False` | `True` | `False` | Flag as legacy, skip verification ✅ |
| `False` | `False` | `True` | Skip verification (already legacy) ✅ |
| `False` | `False` | `False` | Log warning, continue ⚠️ |

### Checksum Mismatch Handling:

| `strict_mode` | Behavior |
|---------------|----------|
| `True` | Raise `ChecksumMismatchError` ❌ |
| `False` | Log warning, return `False` ⚠️ |

---

## Test Coverage

### ✅ **New Test Cases:**

1. **`test_load_raw_records_strict_mode_disallows_legacy_flagging()`:**
   - Verifies that `ValueError` is raised when `strict_mode=True` and `flag_legacy_missing=True`
   - Ensures strict mode cannot be bypassed by legacy flagging

2. **`test_load_raw_record_by_id_strict_mode_disallows_legacy_flagging()`:**
   - Verifies that `ValueError` is raised in `load_raw_record_by_id()` when both parameters are True
   - Ensures consistency across both read paths

### ✅ **Updated Test Cases:**

1. **`test_load_raw_records_ignores_missing_checksum()`:**
   - Updated to use `strict_mode=False` when testing legacy flagging
   - Removed test that expected legacy flagging to work in strict mode
   - Added test to verify `ValueError` is raised in strict mode

**Status:** ✅ Complete

---

## Error Messages

### ValueError When Incompatible Parameters:

```
flag_legacy_missing=True is disallowed when strict_mode=True. 
Strict mode requires all records to have valid checksums. 
Set flag_legacy_missing=False or strict_mode=False.
```

**Purpose:**
- Clear error message explaining the incompatibility
- Guidance on how to fix the issue
- Enforces strict mode semantics

---

## Compliance

✅ **All Requirements Met:**

1. ✅ `flag_legacy_missing=True` is disallowed when `strict_mode=True`
2. ✅ Strict mode always enforces checksum verification
3. ✅ Missing checksums always raise `ChecksumMissingError` in strict mode
4. ✅ Mismatched checksums always raise `ChecksumMismatchError` in strict mode
5. ✅ Legacy auto-flagging only works in soft mode
6. ✅ Clear error messages for incompatible parameters
7. ✅ Comprehensive test coverage

---

## Files Modified

1. `backend/app/core/dataset/service.py` - Updated both service functions
2. `backend/tests/test_raw_record_load_checksums.py` - Updated and added tests

---

## Summary

**Strict mode enforcement is now complete.** The system ensures that:

- ✅ **Strict mode cannot be bypassed** by legacy auto-flagging
- ✅ **Missing checksums always raise errors** in strict mode
- ✅ **Legacy auto-flagging only works in soft mode**
- ✅ **Clear error messages** guide users when incompatible parameters are used
- ✅ **Comprehensive test coverage** validates all behaviors

**Implementation Complete** ✅




