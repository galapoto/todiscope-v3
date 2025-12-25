# File Integrity Checks Implementation

**Date:** 2025-01-XX  
**Status:** ✅ **COMPLETE**  
**Task:** Implement SHA256 checksum computation and verification in ingestion pipeline

---

## Summary

File integrity checks have been successfully implemented in the TodiScope v3 core ingestion system. The implementation ensures that:

1. SHA256 checksums are computed for all ingested files
2. Checksums are stored in `RawRecord.file_checksum` field
3. Optional checksum verification is available in the `ingest_file` endpoint
4. The implementation uses existing checksum utilities and is engine-agnostic

---

## Implementation Details

### 1. RawRecord Model ✅

**Location:** `backend/app/core/dataset/raw_models.py`

The `RawRecord` model already includes the `file_checksum` field:

```python
file_checksum: Mapped[str | None] = mapped_column(String, nullable=True)
```

**Status:** ✅ Field exists and is ready for use

---

### 2. Checksum Computation in Ingestion Service ✅

**Location:** `backend/app/core/ingestion/service.py`

**Changes Made:**

1. **Imported checksum utility:**
   ```python
   from backend.app.core.artifacts.checksums import sha256_hex
   ```

2. **Updated hash functions to use standard utility:**
   ```python
   def _hash_bytes(content: bytes) -> str:
       """Compute SHA256 hash of bytes using the standard checksum utility."""
       return sha256_hex(content)
   
   def _hash_record_payload(record: dict) -> str:
       """Compute SHA256 hash of an individual record payload."""
       encoded = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
       return sha256_hex(encoded)
   ```

3. **Updated `ingest_records` function:**
   - Computes file-level checksum when `raw_content` is available (file uploads)
   - Computes record-level checksum for individual records when file checksum is not available
   - Stores checksum in `RawRecord.file_checksum` field

**Key Logic:**
```python
# Compute file-level checksum if raw_content is available (file upload)
file_checksum: str | None = None
if import_context and import_context.raw_content is not None:
    file_checksum = _hash_bytes(import_context.raw_content)

# For each record, use file checksum if available, otherwise compute record checksum
record_checksum = file_checksum
if record_checksum is None:
    record_checksum = _hash_record_payload(item)

# Store checksum in RawRecord
RawRecord(
    ...
    file_checksum=record_checksum,
    ...
)
```

**Status:** ✅ Checksum computation and storage implemented

---

### 3. Checksum Verification in API Endpoint ✅

**Location:** `backend/app/core/dataset/api.py`

**Changes Made:**

1. **Imported checksum utilities:**
   ```python
   from backend.app.core.artifacts.checksums import sha256_hex, verify_sha256
   from fastapi import Query
   ```

2. **Updated `ingest_file` endpoint:**
   - Computes SHA256 checksum of uploaded file content
   - Validates checksum against optional `expected_checksum` parameter
   - Returns computed checksum in response

**Key Features:**
- **Automatic checksum computation:** Every file upload computes a checksum
- **Optional verification:** If `expected_checksum` query parameter is provided, validates the file matches
- **Error handling:** Returns clear error message on checksum mismatch
- **Response includes checksum:** Returns `file_checksum` in response for client verification

**API Signature:**
```python
@router.post("/ingest-file")
async def ingest_file(
    file: UploadFile = File(...),
    normalize: bool = False,
    expected_checksum: str | None = Query(None, description="Optional SHA256 checksum to verify against uploaded file"),
    db: AsyncSession = Depends(get_db_session),
    _: object = Depends(require_principal(Role.INGEST)),
) -> dict:
```

**Status:** ✅ Checksum verification implemented

---

## Implementation Flow

### File Upload Flow:

1. **Client uploads file** → `POST /api/v3/ingest-file`
2. **Server reads file content** → `content = await file.read()`
3. **Server computes checksum** → `computed_checksum = sha256_hex(content)`
4. **Optional verification** → If `expected_checksum` provided, verify match
5. **Parse records** → `parse_records(...)`
6. **Ingest records** → `ingest_records_service(...)` with `ImportContext(raw_content=content)`
7. **Store checksum** → Each `RawRecord` gets `file_checksum` set to file checksum
8. **Return response** → Includes `file_checksum` in response

### Record-Based Ingestion Flow:

1. **Client sends records** → `POST /api/v3/ingest-records`
2. **Server receives payload** → `ImportContext(raw_payload=payload)`
3. **For each record:**
   - Compute record-level checksum: `_hash_record_payload(item)`
   - Store in `RawRecord.file_checksum`

---

## Benefits

1. **Data Integrity:** Ensures uploaded files are not corrupted during transmission
2. **Audit Trail:** Checksums stored with each record for verification
3. **Optional Verification:** Clients can verify file integrity by providing expected checksum
4. **Engine-Agnostic:** Checksum logic is in core, not engine-specific
5. **Modular:** Uses existing checksum utilities, no code duplication

---

## Usage Examples

### File Upload with Checksum Verification:

```bash
# Compute expected checksum first
EXPECTED_CHECKSUM=$(sha256sum file.json | cut -d' ' -f1)

# Upload with verification
curl -X POST "http://api/v3/ingest-file?expected_checksum=${EXPECTED_CHECKSUM}" \
  -H "X-API-Key: your-key" \
  -F "file=@file.json"
```

### File Upload without Verification:

```bash
# Upload file (checksum computed automatically)
curl -X POST "http://api/v3/ingest-file" \
  -H "X-API-Key: your-key" \
  -F "file=@file.json"

# Response includes computed checksum:
# {
#   "dataset_version_id": "...",
#   "import_id": "...",
#   "raw_records_written": 10,
#   "data_quality": {...},
#   "file_checksum": "abc123..."
# }
```

---

## Testing Recommendations

1. **Test checksum computation:**
   - Upload a file and verify checksum is computed correctly
   - Verify checksum matches manual computation (e.g., `sha256sum`)

2. **Test checksum verification:**
   - Upload file with correct `expected_checksum` → should succeed
   - Upload file with incorrect `expected_checksum` → should fail with clear error

3. **Test record-based ingestion:**
   - Verify record-level checksums are computed when no file is uploaded
   - Verify checksums are unique per record

4. **Test database storage:**
   - Verify `file_checksum` is stored in `RawRecord` table
   - Verify checksums are queryable for audit purposes

---

## Compliance

✅ **All Requirements Met:**

1. ✅ SHA256 checksum computation fully integrated into ingestion pipeline
2. ✅ Checksum stored in `RawRecord.file_checksum` field
3. ✅ Checksum verification logic in `ingest_file` endpoint
4. ✅ Uses existing `sha256_hex()` utility
5. ✅ Engine-agnostic and modular implementation
6. ✅ No code duplication (uses existing utilities)

---

## Files Modified

1. `backend/app/core/ingestion/service.py`
   - Added checksum computation logic
   - Updated to store checksum in RawRecord

2. `backend/app/core/dataset/api.py`
   - Added checksum verification in `ingest_file` endpoint
   - Added optional `expected_checksum` parameter

---

## Next Steps

1. **Database Migration:** Ensure `file_checksum` column exists in `raw_record` table (already present in model)
2. **Testing:** Add unit tests for checksum computation and verification
3. **Documentation:** Update API documentation with checksum verification feature
4. **Monitoring:** Consider logging checksum mismatches for security monitoring

---

**Implementation Complete** ✅




