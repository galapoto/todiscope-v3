"""
OCR (Optical Character Recognition) API endpoints.

Provides endpoints for uploading documents (PDFs, images) and extracting text.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.artifacts.checksums import sha256_hex
from backend.app.core.artifacts.store import get_artifact_store
from backend.app.core.auth.dependencies import require_principal
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.db import get_db_session
from backend.app.core.evidence.models import EvidenceRecord
from backend.app.core.rbac.roles import Role
from backend.app.core.ocr.service import extract_text_from_file


router = APIRouter(prefix="/api/v3/ocr", tags=["ocr"])


@router.post("/upload")
async def upload_ocr_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    principal: object = Depends(require_principal(Role.EXECUTE)),
) -> dict:
    """
    Upload a file for OCR processing.
    
    Supported formats: PDF, PNG, JPEG, JPG
    Max file size: 10MB
    
    Args:
        file: The file to process (PDF or image)
        db: Database session
        principal: Authenticated principal with EXECUTE role
    
    Returns:
        Dictionary containing evidence record, extracted text, confidence, and low confidence sections
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"UNSUPPORTED_FILE_TYPE: {file.content_type}. Supported types: {', '.join(allowed_types)}",
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"FILE_TOO_LARGE: File size {len(file_content)} bytes exceeds maximum {max_size} bytes",
        )
    
    # Calculate checksum
    file_checksum = sha256_hex(file_content)
    
    # Create a dataset version for this OCR upload
    created_at = datetime.now(timezone.utc)
    dataset_version = DatasetVersion(id=str(uuid7()))
    db.add(dataset_version)
    await db.commit()
    await db.refresh(dataset_version)
    
    # Store file in artifact store
    store = get_artifact_store()
    file_key = f"ocr/{file_checksum[:8]}/{file.filename or 'uploaded_file'}"
    stored_artifact = await store.put_bytes(
        key=file_key,
        data=file_content,
        content_type=file.content_type or "application/octet-stream",
    )
    
    # Extract text using OCR service
    try:
        ocr_result = await extract_text_from_file(
            file_content=file_content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "uploaded_file",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR_PROCESSING_FAILED: {type(e).__name__}: {str(e)}",
        ) from e
    
    # Create evidence record
    evidence_id = f"ocr-{uuid4().hex[:16]}"
    
    evidence_record = EvidenceRecord(
        evidence_id=evidence_id,
        dataset_version_id=dataset_version.id,
        engine_id="ocr",
        kind="document",
        payload={
            "file_name": file.filename or "uploaded_file",
            "file_type": file.content_type or "application/octet-stream",
            "file_url": stored_artifact.uri,
            "file_checksum": file_checksum,
            "file_size_bytes": len(file_content),
            "ocr_text": ocr_result["extracted_text"],
            "ocr_confidence": ocr_result["confidence"],
            "ocr_low_confidence_sections": ocr_result.get("low_confidence_sections", []),
        },
        created_at=created_at,
    )
    
    db.add(evidence_record)
    await db.commit()
    await db.refresh(evidence_record)
    
    # Return response matching frontend expectations
    return {
        "evidence": {
            "id": evidence_id,
            "type": "document",
            "status": "completed",
            "source_engine": "ocr",
            "timestamp": created_at.isoformat(),
            "file_name": file.filename or "uploaded_file",
            "file_type": file.content_type or "application/octet-stream",
            "file_url": stored_artifact.uri,
            "ocr_text": ocr_result["extracted_text"],
            "ocr_confidence": ocr_result["confidence"],
            "ocr_low_confidence_sections": ocr_result.get("low_confidence_sections", []),
        },
        "extracted_text": ocr_result["extracted_text"],
        "confidence": ocr_result["confidence"],
        "low_confidence_sections": ocr_result.get("low_confidence_sections", []),
        "dataset_version_id": dataset_version.id,
    }

