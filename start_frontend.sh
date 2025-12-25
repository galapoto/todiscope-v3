#!/bin/bash
# Start the Next.js frontend (frontend/web) from the project root

cd "$(dirname "$0")"

PORT=3400

kill_port() {
  local P=$1
  local PIDS=""

  if command -v fuser >/dev/null 2>&1; then
    PIDS=$(fuser -n tcp "$P" 2>/dev/null || true)
  elif command -v lsof >/dev/null 2>&1; then
    PIDS=$(lsof -ti "tcp:$P" 2>/dev/null || true)
  fi

  if [ -z "$PIDS" ]; then
    return 0
  fi

  echo "Killing process(es) $PIDS on port $P..."
  for PID in $PIDS; do
    kill -TERM "$PID" 2>/dev/null || true
  done
  sleep 1
  for PID in $PIDS; do
    kill -0 "$PID" 2>/dev/null && kill -KILL "$PID" 2>/dev/null || true
  done
}

kill_port 3400
kill_port 3000

echo "Starting frontend..."
cd frontend/web
# Optional: export CLEAN_NEXT=1 to wipe the build cache before starting.
if [ "${CLEAN_NEXT:-0}" = "1" ]; then
  echo "CLEAN_NEXT=1 set; removing frontend/web/.next ..."
  rm -rf .next
fi
npm run dev
