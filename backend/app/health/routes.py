from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Response
from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord

router = APIRouter()


@router.get("/health")
async def health(response: Response) -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, dict[str, Any]] = {}
    overall_ok = True

    if not settings.database_url:
        checks["database"] = {"status": "not_configured"}
        checks["evidence_linking"] = {"status": "skipped"}
    else:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            db_start = time.perf_counter()
            try:
                await db.scalar(select(DatasetVersion.id).limit(1))
                checks["database"] = {
                    "status": "ok",
                    "latency_ms": (time.perf_counter() - db_start) * 1000,
                }
            except Exception as exc:  # pragma: no cover - depends on DB state
                overall_ok = False
                checks["database"] = {
                    "status": "error",
                    "latency_ms": (time.perf_counter() - db_start) * 1000,
                    "detail": str(exc),
                }

            link_start = time.perf_counter()
            try:
                await db.scalar(select(EvidenceRecord.evidence_id).limit(1))
                await db.scalar(select(FindingRecord.finding_id).limit(1))
                await db.scalar(select(FindingEvidenceLink.link_id).limit(1))
                checks["evidence_linking"] = {
                    "status": "ok",
                    "latency_ms": (time.perf_counter() - link_start) * 1000,
                }
            except Exception as exc:  # pragma: no cover - depends on DB state
                overall_ok = False
                checks["evidence_linking"] = {
                    "status": "error",
                    "latency_ms": (time.perf_counter() - link_start) * 1000,
                    "detail": str(exc),
                }

    response.status_code = 200 if overall_ok else 503
    return {
        "status": "ok" if overall_ok else "degraded",
        "checks": checks,
    }
