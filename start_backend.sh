#!/bin/bash
# Start the backend server from the project root

cd "$(dirname "$0")"

# Kill any process using port 8400
PORT=8400
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "Killing process $PID on port $PORT..."
    kill -9 $PID 2>/dev/null
    sleep 1
fi

source .venv/bin/activate

# Default to a local SQLite database for dev if not provided.
if [ -z "$TODISCOPE_DATABASE_URL" ]; then
  export TODISCOPE_DATABASE_URL="sqlite+aiosqlite:///./todiscope-dev.db"
  echo "TODISCOPE_DATABASE_URL not set; defaulting to $TODISCOPE_DATABASE_URL"
fi

# Enable all engines by default for local dev (frontend parity checks expect endpoints to exist).
if [ -z "$TODISCOPE_ENABLED_ENGINES" ]; then
  export TODISCOPE_ENABLED_ENGINES="engine_csrd,engine_financial_forensics,engine_construction_cost_intelligence,engine_audit_readiness,engine_enterprise_capital_debt_readiness,engine_data_migration_readiness,engine_erp_integration_readiness,engine_enterprise_deal_transaction_readiness,engine_enterprise_litigation_dispute,engine_regulatory_readiness,engine_enterprise_insurance_claim_forensics,engine_distressed_asset_debt_stress"
  echo "TODISCOPE_ENABLED_ENGINES not set; defaulting to all engines"
fi

# Since the package is installed, we can run from anywhere
echo "Starting backend on port $PORT..."
PYTHONPATH=. uvicorn backend.app.main:app --reload --port $PORT
