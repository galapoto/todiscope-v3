#!/usr/bin/env python3
"""
Migration Execution Script: Remove parameters column from calculation_run table

This script executes the migration to drop the duplicate 'parameters' column,
keeping only 'parameter_payload' as the single source of truth.

Usage:
    python backend/migrations/execute_migration.py [--dry-run] [--verify-only]

Options:
    --dry-run: Show what would be executed without making changes
    --verify-only: Only verify current state, don't execute migration

Note: This script can be run with or without a virtual environment.
      It will attempt to import backend modules, but will provide helpful
      error messages if dependencies are missing.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import backend modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError as e:
    print("❌ Error: Required dependencies not found.")
    print(f"   Missing: {e}")
    print()
    print("Please install dependencies:")
    print("  1. Activate virtual environment: source .venv/bin/activate")
    print("  2. Install: pip install -e backend")
    print()
    print("Or install globally: pip install sqlalchemy[asyncio]")
    sys.exit(1)

try:
    from backend.app.core.db import get_sessionmaker
except ImportError as e:
    print("❌ Error: Cannot import backend modules.")
    print(f"   Missing: {e}")
    print()
    print("Please ensure:")
    print("  1. You're in the project root directory")
    print("  2. Backend package is installed: pip install -e backend")
    print("  3. Virtual environment is activated (if using one)")
    sys.exit(1)

from backend.app.core.db import get_sessionmaker


async def check_table_exists(db: AsyncSession, table_name: str) -> bool:
    """Check if a table exists."""
    result = await db.execute(
        text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = :table_name
        """),
        {"table_name": table_name},
    )
    return result.scalar() is not None


async def check_column_exists(db: AsyncSession, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await db.execute(
        text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name 
              AND column_name = :column_name
        """),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() is not None


async def verify_pre_migration_state(db: AsyncSession) -> dict:
    """Verify the state before migration."""
    # First check if table exists
    table_exists = await check_table_exists(db, "calculation_run")
    
    if not table_exists:
        return {
            "table_exists": False,
            "parameters_exists": False,
            "parameter_payload_exists": False,
            "parameters_hash_exists": False,
            "record_count": 0,
        }
    
    state = {
        "table_exists": True,
        "parameters_exists": await check_column_exists(db, "calculation_run", "parameters"),
        "parameter_payload_exists": await check_column_exists(db, "calculation_run", "parameter_payload"),
        "parameters_hash_exists": await check_column_exists(db, "calculation_run", "parameters_hash"),
    }
    
    # Check record count
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM calculation_run"))
        state["record_count"] = result.scalar() or 0
    except Exception:
        state["record_count"] = 0
    
    return state


async def execute_migration(db: AsyncSession, dry_run: bool = False) -> bool:
    """Execute the migration."""
    migration_sql = """
        ALTER TABLE calculation_run DROP COLUMN IF EXISTS parameters;
    """
    
    if dry_run:
        print("🔍 DRY RUN - Would execute:")
        print(migration_sql)
        return True
    
    try:
        await db.execute(text(migration_sql))
        await db.commit()
        return True
    except Exception as e:
        await db.rollback()
        print(f"❌ Migration failed: {e}")
        return False


async def verify_post_migration_state(db: AsyncSession) -> dict:
    """Verify the state after migration."""
    state = {
        "parameters_exists": await check_column_exists(db, "calculation_run", "parameters"),
        "parameter_payload_exists": await check_column_exists(db, "calculation_run", "parameter_payload"),
        "parameters_hash_exists": await check_column_exists(db, "calculation_run", "parameters_hash"),
    }
    return state


async def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Execute calculation_run migration")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be executed")
    parser.add_argument("--verify-only", action="store_true", help="Only verify current state")
    args = parser.parse_args()
    
    try:
        sessionmaker = get_sessionmaker()
    except RuntimeError as e:
        if "TODISCOPE_DATABASE_URL" in str(e) or "Database not configured" in str(e):
            print("❌ Error: Database not configured.")
            print()
            print("Please set the TODISCOPE_DATABASE_URL environment variable:")
            print("  export TODISCOPE_DATABASE_URL='postgresql+asyncpg://user:password@host:port/database'")
            print()
            print("Or use direct SQL execution instead:")
            print("  psql -h <host> -U <user> -d <database> -f backend/migrations/remove_calculation_run_parameters_column.sql")
            return
        raise
    
    async with sessionmaker() as db:
        print("=" * 60)
        print("Migration: Remove parameters column from calculation_run")
        print("=" * 60)
        print()
        
        # Pre-migration verification
        print("📋 Pre-Migration State:")
        pre_state = await verify_pre_migration_state(db)
        
        if not pre_state.get("table_exists", False):
            print("  - calculation_run table: DOES NOT EXIST")
            print("  - parameters column: N/A (table doesn't exist)")
            print("  - parameter_payload column: N/A (table doesn't exist)")
            print("  - parameters_hash column: N/A (table doesn't exist)")
            print("  - Total records: 0")
            print()
            print("ℹ️  The calculation_run table does not exist yet.")
            print("   This migration is only needed if the table exists with the old schema.")
            print("   If you're setting up a fresh database, you can skip this migration.")
            print("   The table will be created with the correct schema (without parameters column).")
            print()
            if args.verify_only:
                print("✅ Verification complete (verify-only mode)")
            else:
                print("✅ Migration not needed - table doesn't exist")
            return
        
        print(f"  - calculation_run table: EXISTS")
        print(f"  - parameters column exists: {pre_state['parameters_exists']}")
        print(f"  - parameter_payload column exists: {pre_state['parameter_payload_exists']}")
        print(f"  - parameters_hash column exists: {pre_state['parameters_hash_exists']}")
        print(f"  - Total records: {pre_state['record_count']}")
        print()
        
        if args.verify_only:
            print("✅ Verification complete (verify-only mode)")
            return
        
        # Check if migration is needed
        if not pre_state["parameters_exists"]:
            print("✅ Migration not needed - parameters column already removed")
            return
        
        if not pre_state["parameter_payload_exists"]:
            print("❌ ERROR: parameter_payload column does not exist!")
            print("   Cannot proceed with migration - parameter_payload is required")
            return
        
        # Execute migration
        print("🚀 Executing migration...")
        success = await execute_migration(db, dry_run=args.dry_run)
        
        if args.dry_run:
            print("✅ Dry run complete - no changes made")
            return
        
        if not success:
            print("❌ Migration failed")
            return
        
        # Post-migration verification
        print()
        print("📋 Post-Migration State:")
        post_state = await verify_post_migration_state(db)
        print(f"  - parameters column exists: {post_state['parameters_exists']}")
        print(f"  - parameter_payload column exists: {post_state['parameter_payload_exists']}")
        print(f"  - parameters_hash column exists: {post_state['parameters_hash_exists']}")
        print()
        
        # Verify success
        if (
            not post_state["parameters_exists"]
            and post_state["parameter_payload_exists"]
            and post_state["parameters_hash_exists"]
        ):
            print("✅ Migration successful!")
            print()
            print("Next steps:")
            print("  1. Verify application starts without errors")
            print("  2. Test CalculationRun creation")
            print("  3. Monitor application logs")
        else:
            print("❌ Migration verification failed")
            print("   Expected: parameters=False, parameter_payload=True, parameters_hash=True")
            print(f"   Got: {post_state}")


if __name__ == "__main__":
    asyncio.run(main())

