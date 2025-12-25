# Quick Start Guide

## 🚀 Starting the Servers

### Backend (FastAPI)

**❌ WRONG - Don't do this:**
```bash
cd backend
PYTHONPATH=. uvicorn backend.app.main:app ...  # This won't work!
```

**✅ CORRECT - Choose one:**

**Option 1: Use the script (easiest - automatically kills port if in use)**
```bash
cd /home/vitus-idi/Documents/todiscope-v3
./start_backend.sh
```

The script automatically kills any process using port 8400 before starting.

**Option 2: Since package is installed (run from anywhere)**
```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8400
```

**Option 3: From project root**
```bash
cd /home/vitus-idi/Documents/todiscope-v3
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.app.main:app --reload --port 8400
```

---

### Frontend (Next.js)

**❌ WRONG - Don't do this:**
```bash
cd frontend
npm run dev  # No package.json here!
```

**✅ CORRECT - Choose one:**

**Option 1: Use the script (easiest - automatically kills ports if in use)**
```bash
cd /home/vitus-idi/Documents/todiscope-v3
./start_frontend.sh
```

The script automatically kills any process using port 3400 and removes lock files before starting.

**Option 2: Manual**
```bash
cd frontend/web
npm run dev
```

---

## 📍 Key Points

1. **Backend**: The `backend` module must be importable. This works when:
   - Package is installed (you can run from anywhere)
   - OR you run from project root with `PYTHONPATH=.`
   - ❌ Running from `backend/` directory will NOT work

2. **Frontend**: Next.js app is in `frontend/web/`, not `frontend/`

3. **Port conflicts**: 
   - Backend: `./kill_port_8400.sh`
   - Frontend: Script handles it automatically

---

## 🔧 Troubleshooting

### Backend: "No module named 'backend'"
- **Solution**: Run from project root, not from `backend/` directory
- Or use: `./start_backend.sh`

### Frontend: "Could not read package.json"
- **Solution**: Go to `frontend/web/` directory
- Or use: `./start_frontend.sh`

### Port already in use
- Backend: `./kill_port_8400.sh`
- Frontend: Script handles it automatically

