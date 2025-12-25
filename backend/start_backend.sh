#!/bin/bash
# Convenience wrapper so developers can run `./start_backend.sh` from `backend/`.

cd "$(dirname "$0")/.."
exec ./start_backend.sh
