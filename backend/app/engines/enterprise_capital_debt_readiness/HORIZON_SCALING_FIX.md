# Time-Horizon Mismatch Fix - DSCR and Interest Coverage

## Issue Summary

The debt service logic had a time-horizon mismatch where annual cash/EBITDA metrics were being compared against horizon-scaled debt service totals, causing inaccurate DSCR and interest coverage calculations when `horizon_months` was not 12.

## Problem

### Before Fix:
- **DSCR Calculation**: `cash_available_annual / debt_service_total_horizon`
  - Numerator: Annual cash (e.g., $120,000/year)
  - Denominator: Horizon-scaled debt service (e.g., $30,000 for 6 months)
  - Result: Incorrect ratio (e.g., 4.0 instead of 2.0)

- **Interest Coverage Calculation**: `ebitda_annual / interest_total_horizon`
  - Numerator: Annual EBITDA (e.g., $200,000/year)
  - Denominator: Horizon-scaled interest (e.g., $25,000 for 6 months)
  - Result: Incorrect ratio (e.g., 8.0 instead of 4.0)

### Root Cause:
The debt service schedule correctly scales to `horizon_months`, but the cash/EBITDA metrics remained annual, creating a mismatch between numerator and denominator time periods.

## Solution

### After Fix:
- **DSCR Calculation**: `cash_available_horizon / debt_service_total_horizon`
  - Numerator: Annual cash scaled to horizon (e.g., $120,000 * 6/12 = $60,000)
  - Denominator: Horizon-scaled debt service (e.g., $30,000 for 6 months)
  - Result: Correct ratio (e.g., 2.0)

- **Interest Coverage Calculation**: `ebitda_horizon / interest_total_horizon`
  - Numerator: Annual EBITDA scaled to horizon (e.g., $200,000 * 6/12 = $100,000)
  - Denominator: Horizon-scaled interest (e.g., $25,000 for 6 months)
  - Result: Correct ratio (e.g., 4.0)

### Scaling Formula:
```python
horizon_scale_factor = horizon_months / 12
cash_available_horizon = cash_available_annual * horizon_scale_factor
ebitda_horizon = ebitda_annual * horizon_scale_factor
```

## Changes Made

### 1. Code Changes (`debt_service.py`)

#### DSCR Fix:
- Renamed `cash_available` to `cash_available_annual` for clarity
- Added `cash_available_horizon` calculation with scaling
- Updated DSCR calculation to use scaled value

#### Interest Coverage Fix:
- Renamed `ebitda` to `ebitda_annual` for clarity
- Added `ebitda_horizon` calculation with scaling
- Updated interest coverage calculation to use scaled value

#### Flag Updates:
- Updated flags to reference `cash_available_horizon` and `ebitda_horizon`

### 2. Documentation Changes

#### Assumption Records:
- Updated `assumption_debt_service_horizon` to mention scaling
- Added new `assumption_horizon_scaling` record documenting:
  - Scaling formula: `annual_value * (horizon_months / 12)`
  - Impact: Ensures numerator/denominator consistency
  - Sensitivity: Critical when `horizon_months != 12`

### 3. Test Coverage

Created comprehensive test suite (`test_debt_service_horizon_scaling.py`):

- ✅ `test_dscr_scaling_12_month_horizon()` - Baseline (no scaling)
- ✅ `test_dscr_scaling_6_month_horizon()` - 6-month scaling
- ✅ `test_dscr_scaling_24_month_horizon()` - 24-month scaling
- ✅ `test_interest_coverage_scaling_12_month_horizon()` - Baseline
- ✅ `test_interest_coverage_scaling_6_month_horizon()` - 6-month scaling
- ✅ `test_dscr_consistency_across_horizons()` - Consistency verification
- ✅ `test_ebitda_derived_cash_scaling()` - EBITDA-derived cash scaling
- ✅ `test_noi_derived_cash_scaling()` - NOI-derived cash scaling
- ✅ `test_scaling_assumption_documented()` - Assumption documentation

## Verification

### Test Results:
All tests verify:
1. DSCR values are consistent across different horizons (6, 12, 24 months)
2. Interest coverage values are consistent across different horizons
3. Scaling factor is correctly applied (horizon_months / 12)
4. Assumption is documented in evidence payload

### Example Verification:

**Scenario**: Annual cash = $120,000, Annual debt service = $60,000

| Horizon | Cash (Scaled) | Debt Service | DSCR | Expected |
|---------|---------------|--------------|------|----------|
| 6 months | $60,000 | ~$30,000 | ~2.0 | ✅ Correct |
| 12 months | $120,000 | ~$60,000 | ~2.0 | ✅ Correct |
| 24 months | $240,000 | ~$120,000 | ~2.0 | ✅ Correct |

## Impact

### Before Fix:
- DSCR and interest coverage were inaccurate when `horizon_months != 12`
- Ratios were inflated (for shorter horizons) or deflated (for longer horizons)
- Could lead to incorrect ability level assessments

### After Fix:
- DSCR and interest coverage are accurate for any horizon
- Ratios remain consistent across different horizons
- Ability level assessments are correct

## Compliance

- ✅ **No architectural changes**: Only calculation logic modified
- ✅ **Deterministic**: Scaling uses Decimal arithmetic, no randomness
- ✅ **Documented**: Assumption clearly documented in evidence payload
- ✅ **Tested**: Comprehensive test coverage across multiple horizons
- ✅ **Backward compatible**: Default horizon (12 months) behavior unchanged

## Files Modified

1. `backend/app/engines/enterprise_capital_debt_readiness/debt_service.py`
   - Fixed DSCR calculation scaling
   - Fixed interest coverage calculation scaling
   - Added scaling assumption documentation

2. `backend/tests/engine_enterprise_capital_debt_readiness/test_debt_service_horizon_scaling.py`
   - New comprehensive test suite for horizon scaling

## Related Issues

- Fixes time-horizon mismatch in DSCR calculation
- Fixes time-horizon mismatch in interest coverage calculation
- Ensures consistency between numerator and denominator

---

**Fix Date:** 2025-01-XX  
**Status:** ✅ Complete and Tested


