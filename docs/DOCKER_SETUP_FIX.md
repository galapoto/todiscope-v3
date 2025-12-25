# Docker Setup Fix

**Issue:** Permission denied when accessing Docker socket

## Quick Fix

You need to either:

### Option 1: Add User to Docker Group (Recommended)

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in (or run):
newgrp docker

# Verify
docker ps
```

### Option 2: Use sudo (Temporary)

```bash
# Start database with sudo
sudo docker-compose -f infra/docker-compose.yml up -d db

# Check status
sudo docker-compose -f infra/docker-compose.yml ps db
```

---

## After Fixing Permissions

Once Docker is accessible:

```bash
# 1. Start database
docker-compose -f infra/docker-compose.yml up -d db

# 2. Wait for database to be ready
sleep 5

# 3. Set connection
export TODISCOPE_DATABASE_URL='postgresql+asyncpg://todiscope:todiscope@localhost:5435/todiscope_v3'

# 4. Run migration (from project root)
cd /home/vitus-idi/Documents/todiscope-v3
source .venv/bin/activate
python backend/migrations/execute_migration.py --verify-only
python backend/migrations/execute_migration.py
```

---

## Alternative: Use Direct SQL

If Docker setup is problematic, you can use direct SQL execution once you have database access:

```bash
# Connect and execute
PGPASSWORD=todiscope psql -h localhost -p 5435 -U todiscope -d todiscope_v3 -f backend/migrations/remove_calculation_run_parameters_column.sql
```




