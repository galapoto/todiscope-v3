# Period Boundary Calculation Fixes

**Date:** 2025-01-XX  
**Engineer:** Senior Backend Engineer

---

## Summary

Fixed critical bugs in time-phased reporting period boundary calculations for weekly, monthly, and quarterly periods. The bugs could cause incorrect period boundaries, especially at month and year transitions.

---

## Bugs Fixed

### 1. Weekly Period Boundary Calculation

**Problem:**
- Used `start.replace(day=start.day - days_since_monday)` which could result in invalid day values (negative or 0)
- Example: If `start.day = 1` and `days_since_monday = 3`, this would attempt to set `day = -2`, which is invalid
- Did not handle month/year boundaries correctly when going back to Monday

**Fix:**
- Replaced with `timedelta` arithmetic: `start - timedelta(days=days_since_monday)`
- This robustly handles month/year transitions
- Also fixed end calculation to use `timedelta` for consistency

**Location:** `time_phased/reporter.py:132-137`

**Before:**
```python
days_since_monday = date.weekday()
start = date.replace(hour=0, minute=0, second=0, microsecond=0)
start = start.replace(day=start.day - days_since_monday)  # BUG: Invalid if day < days_since_monday
end = start.replace(day=start.day + 6, hour=23, minute=59, second=59, microsecond=999999)
```

**After:**
```python
days_since_monday = date.weekday()
start = date.replace(hour=0, minute=0, second=0, microsecond=0)
start = start - timedelta(days=days_since_monday)  # FIXED: Robust date arithmetic
end = start + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
```

---

### 2. Monthly Period End Calculation

**Problem:**
- Used `end.replace(day=end.day - 1)` where `end` was set to the first day of the next month
- When `end.day = 1`, this would attempt to set `day = 0`, which is invalid
- Did not correctly handle leap years for February
- Did not correctly handle months with different numbers of days

**Fix:**
- Use `calendar.monthrange(year, month)` to get the actual last day of the month
- This correctly handles:
  - Leap years (February 29 vs 28)
  - Months with 30 vs 31 days
  - Edge cases at year boundaries

**Location:** `time_phased/reporter.py:138-145`

**Before:**
```python
start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
if date.month == 12:
    end = date.replace(year=date.year + 1, month=1, day=1, hour=23, minute=59, second=59, microsecond=999999)
    end = end.replace(day=end.day - 1)  # BUG: Invalid when end.day = 1
else:
    end = date.replace(month=date.month + 1, day=1, hour=23, minute=59, second=59, microsecond=999999)
    end = end.replace(day=end.day - 1)  # BUG: Invalid when end.day = 1
```

**After:**
```python
start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
# Use calendar.monthrange() to get the last day of the month correctly
_, last_day = calendar.monthrange(date.year, date.month)
end = date.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)
```

---

### 3. Quarterly Period End Calculation

**Problem:**
- Same issue as monthly: used `end.replace(day=end.day - 1)` where `end.day = 1`
- This would fail when trying to calculate the last day of a quarter
- Did not correctly handle the last month of quarters (which can have 30 or 31 days)

**Fix:**
- Use `calendar.monthrange(year, month)` to get the actual last day of the quarter-end month
- Simplified logic by directly calculating end month and getting its last day

**Location:** `time_phased/reporter.py:146-156`

**Before:**
```python
quarter = (date.month - 1) // 3
start_month = quarter * 3 + 1
start = date.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
end_month = start_month + 2
if end_month == 12:
    end = date.replace(year=date.year + 1, month=1, day=1, hour=23, minute=59, second=59, microsecond=999999)
    end = end.replace(day=end.day - 1)  # BUG: Invalid when end.day = 1
else:
    end = date.replace(month=end_month + 1, day=1, hour=23, minute=59, second=59, microsecond=999999)
    end = end.replace(day=end.day - 1)  # BUG: Invalid when end.day = 1
```

**After:**
```python
quarter = (date.month - 1) // 3
start_month = quarter * 3 + 1
start = date.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
end_month = start_month + 2
# Use calendar.monthrange() to get the last day of the quarter-end month correctly
_, last_day = calendar.monthrange(date.year, end_month)
end = date.replace(month=end_month, day=last_day, hour=23, minute=59, second=59, microsecond=999999)
```

---

## Test Coverage

Comprehensive test suite added in `test_time_phased_period_bounds.py` covering:

### Weekly Period Tests
- ✅ Start of week (Monday)
- ✅ End of week (Sunday)
- ✅ Mid-week
- ✅ Cross-month boundary
- ✅ Cross-year boundary

### Monthly Period Tests
- ✅ Start of month
- ✅ End of month
- ✅ Mid-month
- ✅ February in leap year (29 days)
- ✅ February in non-leap year (28 days)
- ✅ 30-day months
- ✅ December (year boundary)

### Quarterly Period Tests
- ✅ Q1 (Jan-Mar)
- ✅ Q2 (Apr-Jun)
- ✅ Q3 (Jul-Sep)
- ✅ Q4 (Oct-Dec)
- ✅ Q4 at end of year
- ✅ Leap year February in Q1

### Edge Cases
- ✅ Daily periods
- ✅ Yearly periods
- ✅ January 1 edge cases

**All 22 tests pass.** ✅

---

## Rationale

### Why `timedelta` for Weekly Calculations

- **Robustness**: `timedelta` handles date arithmetic across month and year boundaries automatically
- **Clarity**: More explicit intent (subtract days) vs manipulating day numbers
- **Correctness**: Eliminates possibility of invalid day values

### Why `calendar.monthrange()` for Monthly/Quarterly

- **Accuracy**: Correctly handles leap years and variable month lengths
- **Simplicity**: Eliminates complex conditional logic for year boundaries
- **Reliability**: Uses standard library function designed for this purpose

### Code Simplification

The fixes also simplified the code:
- Monthly: Removed complex year boundary conditional logic
- Quarterly: Removed complex month boundary conditional logic
- Both now use the same reliable pattern: get last day from `calendar.monthrange()`

---

## Impact

### Before Fixes
- ❌ Weekly periods could fail when start date is near beginning of month
- ❌ Monthly periods could fail at year boundaries
- ❌ Quarterly periods could fail at year boundaries
- ❌ Incorrect handling of leap years
- ❌ Potential `ValueError` exceptions when day value becomes invalid

### After Fixes
- ✅ All period types handle edge cases correctly
- ✅ Robust handling of month/year transitions
- ✅ Correct leap year handling
- ✅ No possibility of invalid date values
- ✅ All edge cases tested and passing

---

## Verification

All fixes verified with comprehensive test suite:
- **Test File**: `test_time_phased_period_bounds.py`
- **Test Count**: 22 tests
- **Status**: ✅ All passing
- **Coverage**: All period types and edge cases

---

## Conclusion

The period boundary calculation bugs have been fixed using robust date arithmetic:
- Weekly: `timedelta` for safe date subtraction/addition
- Monthly: `calendar.monthrange()` for accurate last day calculation
- Quarterly: `calendar.monthrange()` for accurate quarter-end calculation

All fixes are backwards-compatible and do not change the API or expected behavior. The fixes only correct incorrect boundary calculations that could occur in edge cases.


