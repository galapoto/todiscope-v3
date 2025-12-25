-- Verification Script: Post-Migration Checks
-- Run this script after executing remove_calculation_run_parameters_column.sql
-- to verify the migration was successful

-- 1. Verify parameters column is dropped
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ PASS: parameters column successfully dropped'
        ELSE '❌ FAIL: parameters column still exists'
    END as migration_status
FROM information_schema.columns 
WHERE table_name = 'calculation_run' 
  AND column_name = 'parameters';

-- 2. Verify parameter_payload column exists
SELECT 
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ PASS: parameter_payload column exists'
        ELSE '❌ FAIL: parameter_payload column missing'
    END as payload_column_status
FROM information_schema.columns 
WHERE table_name = 'calculation_run' 
  AND column_name = 'parameter_payload';

-- 3. Verify parameters_hash column exists
SELECT 
    CASE 
        WHEN COUNT(*) = 1 THEN '✅ PASS: parameters_hash column exists'
        ELSE '❌ FAIL: parameters_hash column missing'
    END as hash_column_status
FROM information_schema.columns 
WHERE table_name = 'calculation_run' 
  AND column_name = 'parameters_hash';

-- 4. Verify table structure (all expected columns)
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'calculation_run'
ORDER BY ordinal_position;

-- 5. Check for any existing records and their data
SELECT 
    COUNT(*) as total_records,
    COUNT(parameter_payload) as records_with_payload,
    COUNT(parameters_hash) as records_with_hash
FROM calculation_run;

-- 6. Sample data verification (if records exist)
SELECT 
    run_id,
    dataset_version_id,
    engine_id,
    engine_version,
    CASE 
        WHEN parameter_payload IS NULL THEN 'NULL'
        WHEN parameter_payload = '{}'::jsonb THEN 'EMPTY'
        ELSE 'POPULATED'
    END as payload_status,
    CASE 
        WHEN parameters_hash IS NULL THEN 'NULL'
        ELSE 'POPULATED'
    END as hash_status
FROM calculation_run
LIMIT 5;





