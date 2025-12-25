-- Migration: Remove duplicate 'parameters' column from calculation_run table
-- Date: 2025-01-XX
-- Description: Removes the duplicate 'parameters' column, keeping only 'parameter_payload'
--              as the single source of truth for calculation parameters.

-- Step 1: Verify that parameter_payload contains the same data as parameters
-- (This should be verified before running the migration)

-- Step 2: Drop the parameters column
ALTER TABLE calculation_run DROP COLUMN IF EXISTS parameters;

-- Note: If you need to preserve data, you can first copy it:
-- UPDATE calculation_run SET parameter_payload = parameters WHERE parameter_payload IS NULL OR parameter_payload = '{}'::jsonb;
-- Then drop the column as above.





