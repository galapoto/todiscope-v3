# Frontend Directory

⚠️ **IMPORTANT:** The frontend application is located in the `web/` subdirectory.

## To Run the Frontend

### Option 1: Using the Start Script (Easiest)

```bash
# From project root
cd /path/to/todiscope-v3
./start_frontend.sh
```

### Option 2: Manual Start

```bash
cd web
npm run dev
```

Or from the project root:

```bash
cd frontend/web
npm run dev
```

### If Port is Already in Use

If you see "Port 3000 is in use" or "Unable to acquire lock":

```bash
# Kill existing Next.js processes
lsof -ti:3000,3001 | xargs kill -9
rm -f frontend/web/.next/dev/lock

# Then start again
cd frontend/web
npm run dev
```

## Project Structure

```
frontend/
├── web/              ← NEXT.JS APP (Go here!)
│   ├── src/
│   ├── package.json
│   └── ...
└── README.md         ← You are here
```

The Next.js application is in `frontend/web/`, not in the root `frontend/` directory.

---

For more details, see `NEXTJS_SETUP.md` in this directory.
