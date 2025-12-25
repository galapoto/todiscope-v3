# Backend (v3 bootstrap)

Minimal FastAPI app + core enforcement modules.

## Running the Backend

### Option 1: Using the Start Script (Easiest)

```bash
# From project root
cd /path/to/todiscope-v3
./start_backend.sh
```

### Option 2: After Package Installation (Recommended)

Since the backend is installed as a package, you can run from **anywhere**:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run from anywhere (no PYTHONPATH needed!)
uvicorn backend.app.main:app --reload --port 8400
```

### Option 3: From Project Root with PYTHONPATH

```bash
# From project root
cd /path/to/todiscope-v3
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8400
```

⚠️ **IMPORTANT:** Do NOT run from inside the `backend/` directory. The imports use `backend.app.main`, which requires Python to find `backend` as a top-level package. This only works when:
- The package is installed (Option 2), OR
- Running from project root with PYTHONPATH (Option 3)

## Alternative: Install as Package (Recommended)

✅ **Install from the project root** (this is now configured correctly):

```bash
# From project root
cd /path/to/todiscope-v3
source .venv/bin/activate  # or your venv
pip install -e backend/
```

After installation, you can run from anywhere:
```bash
uvicorn backend.app.main:app --reload --port 8400
```

**Benefits:**
- No need to set `PYTHONPATH=.` every time
- Can run uvicorn from any directory
- Package is installed in editable mode (changes are reflected immediately)
