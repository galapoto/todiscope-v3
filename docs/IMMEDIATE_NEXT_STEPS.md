# Immediate Next Steps

**Current Status:** Docker installed, but needs permission fix or sudo

---

## Quick Fix Options

### Option 1: Add User to Docker Group (Best - Do This Once)

Run these commands in your terminal:

```bash
# Add yourself to docker group
sudo usermod -aG docker $USER

# Apply the change (choose one):
# A) Log out and log back in
# B) Or run this:
newgrp docker

# Test it works
docker ps
```

**Then run:**
```bash
cd /home/vitus-idi/Documents/todiscope-v3
./run_migration_complete.sh --verify-only
```

---

### Option 2: Use sudo (Quick - But Requires Password Each Time)

Run these commands in your terminal:

```bash
cd /home/vitus-idi/Documents/todiscope-v3

# Start database with sudo
sudo docker-compose -f infra/docker-compose.yml up -d db

# Wait a bit
sleep 5

# Set connection
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'

# Activate venv
source .venv/bin/activate

# Run migration
python backend/migrations/execute_migration.py --verify-only
python backend/migrations/execute_migration.py
```

---

## What to Do Right Now

**In your terminal, run:**

```bash
# 1. Go to project root
cd /home/vitus-idi/Documents/todiscope-v3

# 2. Add yourself to docker group (one-time setup)
sudo usermod -aG docker $USER
newgrp docker

# 3. Start database
docker-compose -f infra/docker-compose.yml up -d db

# 4. Wait and verify
sleep 5
docker-compose -f infra/docker-compose.yml ps db

# 5. Set connection and run migration
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'
source .venv/bin/activate
python backend/migrations/execute_migration.py --verify-only
python backend/migrations/execute_migration.py
```

---

## Expected Output

After running the migration, you should see:

```
============================================================
Migration: Remove parameters column from calculation_run
============================================================

📋 Pre-Migration State:
  - parameters column exists: True
  - parameter_payload column exists: True
  - parameters_hash column exists: True
  - Total records: X

🚀 Executing migration...

📋 Post-Migration State:
  - parameters column exists: False
  - parameter_payload column exists: True
  - parameters_hash column exists: True

✅ Migration successful!
```

---

**Ready to proceed!** Follow the steps above in your terminal.




