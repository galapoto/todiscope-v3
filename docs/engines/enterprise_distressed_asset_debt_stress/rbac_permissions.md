# RBAC Permissions: Enterprise Distressed Asset & Debt Stress Engine

**Engine ID:** `engine_distressed_asset_debt_stress`  
**Documentation Version:** 1.0  
**Last Updated:** 2025-01-XX

---

## Overview

The Enterprise Distressed Asset & Debt Stress Engine implements **explicit Role-Based Access Control (RBAC)** checks at the engine level, in addition to platform-level security. This ensures that sensitive financial operations are properly protected and auditable.

---

## RBAC Roles

### Available Roles

The engine uses the following TodiScope v3 platform roles:

| Role | Description | Engine Access |
|------|-------------|---------------|
| `EXECUTE` | Execute engine operations | Required to run the engine |
| `READ` | Read data access | Required to access DatasetVersion and normalized records |
| `ADMIN` | Administrative access | Full access to all operations |
| `INGEST` | Data ingestion | Not used by engine (platform-level only) |

### Role Hierarchy

- **ADMIN** role has full access to all operations (bypasses other role checks)
- **EXECUTE** role is required for engine execution
- **READ** role is required for data access (enforced at platform level)

---

## Engine-Level RBAC Implementation

### Endpoint Protection

The engine's `/run` endpoint is protected with explicit RBAC checks:

```python
@router.post("/run")
async def run_endpoint(
    payload: dict,
    _: object = Depends(require_principal(Role.EXECUTE)),
) -> dict:
    """
    Execute the Enterprise Distressed Asset & Debt Stress Engine.
    
    RBAC Requirements:
    - Requires EXECUTE role for engine execution
    - Requires READ role for accessing DatasetVersion and normalized records (enforced at platform level)
    - ADMIN role has full access to all operations
    """
    # Engine execution logic...
```

### RBAC Enforcement Points

1. **API Endpoint**: `require_principal(Role.EXECUTE)` dependency
2. **DatasetVersion Access**: Validated before processing (platform-level READ check)
3. **Evidence Creation**: All evidence bound to DatasetVersion (access controlled)
4. **Finding Creation**: All findings bound to DatasetVersion (access controlled)

---

## Permission Requirements

### Engine Execution

**Required Role:** `EXECUTE`

**Operations:**
- Execute engine run
- Generate stress test reports
- Create evidence records
- Create findings

**Access Control:**
- Checked at endpoint level via `require_principal(Role.EXECUTE)`
- Returns `403 FORBIDDEN` if role is missing
- `ADMIN` role bypasses this check

### Data Access

**Required Role:** `READ`

**Operations:**
- Access DatasetVersion records
- Read normalized records
- Query evidence records
- Query findings

**Access Control:**
- Enforced at platform level (middleware/database layer)
- DatasetVersion access validated before engine execution
- Evidence and findings access controlled via DatasetVersion binding

### Administrative Access

**Required Role:** `ADMIN`

**Operations:**
- Full access to all engine operations
- Bypasses all other role checks
- Can execute engine regardless of other permissions

---

## API Key Configuration

### Environment Variable

RBAC is configured via the `TODISCOPE_API_KEYS` environment variable:

```bash
export TODISCOPE_API_KEYS="key1:execute|read,key2:admin,key3:read"
```

### API Key Format

```
<api_key>:<role1>|<role2>|<role3>
```

**Examples:**
- `my-key:execute|read` - Key with EXECUTE and READ roles
- `admin-key:admin` - Key with ADMIN role (full access)
- `read-only-key:read` - Key with READ role only (cannot execute engine)

### API Key Usage

**Request Header:**
```
X-API-Key: <api_key>
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-key" \
  -d '{
    "dataset_version_id": "dv_123",
    "started_at": "2025-01-01T00:00:00Z"
  }'
```

---

## Error Responses

### Authentication Errors

**401 UNAUTHORIZED - AUTH_REQUIRED:**
```json
{
  "detail": "AUTH_REQUIRED"
}
```
**Cause:** Missing `X-API-Key` header when `TODISCOPE_API_KEYS` is configured.

**401 UNAUTHORIZED - AUTH_INVALID:**
```json
{
  "detail": "AUTH_INVALID"
}
```
**Cause:** Invalid API key (not found in `TODISCOPE_API_KEYS`).

### Authorization Errors

**403 FORBIDDEN:**
```json
{
  "detail": "FORBIDDEN"
}
```
**Cause:** API key does not have required `EXECUTE` role.

---

## Security Best Practices

### For API Key Management

1. **Use Strong Keys**: Generate cryptographically secure API keys
2. **Rotate Regularly**: Rotate API keys periodically
3. **Principle of Least Privilege**: Grant minimum required roles
4. **Separate Keys**: Use different keys for different environments (dev, staging, prod)
5. **Secure Storage**: Store API keys securely (environment variables, secrets management)

### For Role Assignment

1. **EXECUTE Role**: Grant only to users/systems that need to run the engine
2. **READ Role**: Grant to users/systems that need to access data
3. **ADMIN Role**: Grant only to administrators (minimal set)
4. **Audit Access**: Log all role assignments and changes

### For Engine Usage

1. **Verify Permissions**: Check user permissions before engine execution
2. **Audit Logging**: All engine operations are logged with user context
3. **DatasetVersion Isolation**: Users can only access DatasetVersions they have permission to view
4. **Evidence Access**: Evidence and findings are bound to DatasetVersion (access controlled)

---

## Audit Logging

### Logged Events

All engine operations are logged with:

- **User Context**: API key identifier (subject)
- **Roles**: Roles granted to the user
- **Operation**: Engine execution
- **DatasetVersion**: DatasetVersion ID processed
- **Timestamp**: Operation timestamp
- **Result**: Success or failure

### Log Format

```
[INFO] Engine execution started: engine=engine_distressed_asset_debt_stress subject=api_key roles=('execute', 'read') dataset_version_id=dv_123
[INFO] Engine execution completed: engine=engine_distressed_asset_debt_stress subject=api_key dataset_version_id=dv_123 evidence_ids=[...]
```

### Access Control Logs

```
[WARN] Access denied: engine=engine_distressed_asset_debt_stress subject=api_key required_role=EXECUTE
[WARN] DatasetVersion access denied: dataset_version_id=dv_123 subject=api_key required_role=READ
```

---

## Examples

### Example 1: Valid Request with EXECUTE Role

**API Key Configuration:**
```bash
export TODISCOPE_API_KEYS="engine-key:execute|read"
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: engine-key" \
  -d '{
    "dataset_version_id": "dv_123",
    "started_at": "2025-01-01T00:00:00Z"
  }'
```

**Result:** ✅ **200 OK** - Engine executes successfully

### Example 2: Request with READ Role Only

**API Key Configuration:**
```bash
export TODISCOPE_API_KEYS="read-only-key:read"
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: read-only-key" \
  -d '{
    "dataset_version_id": "dv_123",
    "started_at": "2025-01-01T00:00:00Z"
  }'
```

**Result:** ❌ **403 FORBIDDEN** - Missing EXECUTE role

### Example 3: Request with ADMIN Role

**API Key Configuration:**
```bash
export TODISCOPE_API_KEYS="admin-key:admin"
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: admin-key" \
  -d '{
    "dataset_version_id": "dv_123",
    "started_at": "2025-01-01T00:00:00Z"
  }'
```

**Result:** ✅ **200 OK** - Admin has full access

### Example 4: Request with Missing API Key

**API Key Configuration:**
```bash
export TODISCOPE_API_KEYS="required-key:execute|read"
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/v3/engines/distressed-asset-debt-stress/run \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_version_id": "dv_123",
    "started_at": "2025-01-01T00:00:00Z"
  }'
```

**Result:** ❌ **401 UNAUTHORIZED** - Missing API key

---

## Integration with Platform Security

### Platform-Level Security

The engine integrates with TodiScope v3 platform security:

1. **Authentication**: Handled by FastAPI middleware
2. **Authorization**: RBAC checks at platform and engine level
3. **Audit Logging**: All operations logged with user context
4. **DatasetVersion Access**: Controlled at platform level

### Engine-Level Security

The engine adds explicit RBAC checks:

1. **Endpoint Protection**: `require_principal(Role.EXECUTE)` dependency
2. **Operation Logging**: All operations logged with user context
3. **Evidence Access**: Evidence bound to DatasetVersion (access controlled)
4. **Finding Access**: Findings bound to DatasetVersion (access controlled)

---

## Summary

1. **Engine implements explicit RBAC checks** at the endpoint level
2. **EXECUTE role required** for engine execution
3. **READ role required** for data access (enforced at platform level)
4. **ADMIN role** has full access to all operations
5. **All operations are logged** with user context for audit purposes
6. **DatasetVersion isolation** ensures users can only access authorized data

---

## References

- **TodiScope v3 RBAC**: `backend/app/core/rbac/`
- **API Reference**: `docs/engines/enterprise_distressed_asset_debt_stress/api_reference.md`
- **Production Deployment**: `backend/app/engines/enterprise_distressed_asset_debt_stress/PRODUCTION_DEPLOYMENT.md`

---

**Document Control**

**Version:** 1.0  
**Last Updated:** 2025-01-XX  
**Author:** Backend Engineering Team  
**Status:** Production Ready






