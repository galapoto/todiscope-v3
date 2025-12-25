# Migration Step-by-Step Guide

**Current Issues:**
1. Docker requires sudo (or user needs to be in docker group)
2. Database is not running yet
3. You're in the `backend/` directory - need to be in project root

---

## Step 1: Fix Docker Permissions (Choose One)

### Option A: Add User to Docker Group (Recommended - Permanent Fix)

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Apply changes (choose one):
# Option 1: Log out and log back in
# Option 2: Run this command:
newgrp docker

# Verify it works
docker ps
```

### Option B: Use sudo (Temporary)

Just use `sudo` for docker commands (shown below).

---

## Step 2: Navigate to Project Root

```bash
cd /home/vitus-idi/Documents/todiscope-v3
```

---

## Step 3: Start Database

**If you added yourself to docker group:**
```bash
docker-compose -f infra/docker-compose.yml up -d db
```

**If using sudo:**
```bash
sudo docker-compose -f infra/docker-compose.yml up -d db
```

**Wait a few seconds, then verify:**
```bash
# Without sudo (if in docker group)
docker-compose -f infra/docker-compose.yml ps db

# With sudo
sudo docker-compose -f infra/docker-compose.yml ps db
```

You should see the database container running.

---

## Step 4: Set Database Connection

```bash
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
```

**Note:** This only lasts for the current terminal session. To make it permanent, add to `~/.bashrc` or create a `.env` file.

---

## Step 5: Activate Virtual Environment

```bash
source .venv/bin/activate
```

---

## Step 6: Run Migration

```bash
# Verify current state
python backend/migrations/execute_migration.py --verify-only

# Execute migration
python backend/migrations/execute_migration.py
```

---

## Complete Command Sequence

**If you're in docker group:**
```bash
cd /home/vitus-idi/Documents/todiscope-v3
docker-compose -f infra/docker-compose.yml up -d db
sleep 5
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
source .venv/bin/activate
python backend/migrations/execute_migration.py --verify-only
python backend/migrations/execute_migration.py
```

**If using sudo:**
```bash
cd /home/vitus-idi/Documents/todiscope-v3
sudo docker-compose -f infra/docker-compose.yml up -d db
sleep 5
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
source .venv/bin/activate
python backend/migrations/execute_migration.py --verify-only
python backend/migrations/execute_migration.py
```

---

## Alternative: Direct SQL Execution

If you prefer not to use Docker or have issues, you can execute the migration directly with `psql`:

**First, install PostgreSQL client:**
```bash
sudo apt install postgresql-client
```

**Then connect and execute:**
```bash
# For Docker Compose database (once it's running)
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql

# Verify
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/verify_migration.sql
```

---

## Troubleshooting

### "Permission denied" for Docker
→ Add user to docker group: `sudo usermod -aG docker $USER` then log out/in

### "Connection refused"
→ Database not running - start it with docker-compose

### "No such file or directory" for migration script
→ Make sure you're in project root (`/home/vitus-idi/Documents/todiscope-v3`), not in `backend/`

---

**Next:** Follow the steps above in order!




