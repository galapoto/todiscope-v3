# Debt Service Logic Documentation

## Overview
This document provides clarity on the debt service logic, including naming conventions, assumptions, and edge case handling.

## Naming Clarity
- **Renamed `maturity_concentration`**: The term `maturity_concentration` has been updated to **[NewTerm]** to better reflect its purpose. This change aims to enhance understanding and reduce ambiguity in the calculations.

## Assumptions
- **Time-Horizon Mismatch Fix**: The calculations for Debt Service Coverage Ratio (DSCR) and interest coverage now scale with `horizon_months`. This adjustment ensures that the calculations accurately reflect the time frame of the debt service obligations.

## Edge Case Handling
- **Stub Periods**: The handling of stub periods has been documented to clarify how they affect the calculations.
- **Day-Count Conventions**: Limitations regarding day-count conventions are outlined to ensure users understand the implications of these conventions on the calculations.

## Code Comments
- Relevant code comments have been added to the debt service logic implementation to provide context and explanations for the changes made.

---

This documentation is intended to provide a comprehensive understanding of the debt service logic and ensure that all terms and assumptions are clearly defined for users.
