"""FastAPI router and registration for the litigation/dispute engine."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.engine_registry.spec import EngineSpec
from backend.app.engines.enterprise_litigation_dispute.constants import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.enterprise_litigation_dispute.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    ImmutableConflictError,
    LegalPayloadMissingError,
    NormalizedRecordMissingError,
    ParametersInvalidError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.enterprise_litigation_dispute.models import EnterpriseLitigationDisputeRun

router = APIRouter(
    prefix="/api/v3/engines/litigation-analysis",
    tags=[ENGINE_ID],
)


@router.post("/run")
async def run_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. Enable via TODISCOPE_ENABLED_ENGINES.",
        )

    from backend.app.engines.enterprise_litigation_dispute.run import run_engine

    try:
        return await run_engine(
            dataset_version_id=payload.get("dataset_version_id"),
            started_at=payload.get("started_at"),
            parameters=payload.get("parameters"),
        )
    except DatasetVersionMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatasetVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StartedAtMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StartedAtInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LegalPayloadMissingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NormalizedRecordMissingError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ParametersInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ImmutableConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ENGINE_RUN_FAILED: {type(exc).__name__}: {exc}") from exc


@router.post("/report")
async def report_endpoint(payload: dict) -> dict:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    from backend.app.engines.enterprise_litigation_dispute.report.assembler import (
        EvidenceNotFoundError,
        FindingsNotFoundError,
        ReportAssemblyError,
        assemble_report,
    )
    from backend.app.engines.enterprise_litigation_dispute.run import _validate_dataset_version_id

    dataset_version_id = payload.get("dataset_version_id")

    try:
        validated_dv_id = _validate_dataset_version_id(dataset_version_id)
    except (DatasetVersionMissingError, DatasetVersionInvalidError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        try:
            return await assemble_report(db, dataset_version_id=validated_dv_id)
        except FindingsNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except EvidenceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReportAssemblyError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"REPORT_GENERATION_FAILED: {type(exc).__name__}: {exc}",
            ) from exc


@router.get("/export", response_model=None)
async def export_report(
    *,
    dataset_version_id: str | None = None,
    run_id: str | None = None,
    format: str = "json",
) -> Response | dict:
    if not is_engine_enabled(ENGINE_ID):
        raise HTTPException(
            status_code=503,
            detail=(
                f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
                "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
            ),
        )

    fmt = format.lower()
    if fmt not in {"json", "pdf"}:
        raise HTTPException(status_code=400, detail="FORMAT_NOT_SUPPORTED")
    if run_id is None and dataset_version_id is None:
        raise HTTPException(status_code=400, detail="DATASET_VERSION_OR_RUN_ID_REQUIRED")

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        if run_id:
            query = select(EnterpriseLitigationDisputeRun).where(
                EnterpriseLitigationDisputeRun.run_id == run_id
            )
        else:
            query = (
                select(EnterpriseLitigationDisputeRun)
                .where(EnterpriseLitigationDisputeRun.dataset_version_id == dataset_version_id)
                .order_by(EnterpriseLitigationDisputeRun.run_start_time.desc())
            )
        run_record = await db.scalar(query)
        if run_record is None:
            raise HTTPException(status_code=404, detail="RUN_NOT_FOUND")

    metadata = {
        "run_id": run_record.run_id,
        "dataset_version_id": run_record.dataset_version_id,
        "status": run_record.status,
        "run_start_time": run_record.run_start_time.isoformat(),
        "run_end_time": run_record.run_end_time.isoformat() if run_record.run_end_time else None,
    }
    report_payload = {"metadata": metadata, "summary": run_record.summary}

    if fmt == "json":
        return report_payload

    pdf_bytes = _build_pdf_report(report_payload)
    filename = f"litigation-report-{run_record.run_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _build_pdf_report(report_payload: dict[str, Any]) -> bytes:
    lines = []
    metadata = report_payload.get("metadata", {})
    summary = report_payload.get("summary", {})
    lines.append("Enterprise Litigation & Dispute Analysis Report")
    lines.append(f"Run ID: {metadata.get('run_id')}")
    lines.append(f"DatasetVersion: {metadata.get('dataset_version_id')}")
    lines.append(f"Status: {metadata.get('status')}")
    lines.append(f"Started: {metadata.get('run_start_time')}")
    lines.append(f"Completed: {metadata.get('run_end_time') or 'pending'}")
    lines.append("")

    damage = summary.get("damage_assessment", {})
    lines.append("Damage Assessment")
    lines.append(f"  Net Damage: {damage.get('net_damage')}")
    lines.append(f"  Severity: {damage.get('severity')}")
    lines.append(f"  Confidence: {damage.get('confidence')}")
    lines.append("")

    scenario = summary.get("scenario_comparison", {})
    best_case = scenario.get("best_case") or {}
    worst_case = scenario.get("worst_case") or {}
    lines.append("Scenario Comparison")
    lines.append(f"  Total Probability: {scenario.get('total_probability')}")
    lines.append(f"  Best Case: {best_case.get('name')} loss={best_case.get('expected_loss')}")
    lines.append(f"  Worst Case: {worst_case.get('name')} loss={worst_case.get('expected_loss')}")
    lines.append("")

    consistency = summary.get("legal_consistency", {})
    lines.append("Legal Consistency")
    lines.append(f"  Consistent: {consistency.get('consistent')}")
    issues = consistency.get("issues") or []
    for issue in issues:
        lines.append(f"    - {issue}")
    lines.append("")

    scenario_evidence = summary.get("evidence", {})
    lines.append("Evidence Map")
    for key, value in scenario_evidence.items():
        lines.append(f"  {key}: {value}")
    lines.append("")

    assumptions = summary.get("assumptions") or []
    lines.append(f"Assumptions documented: {len(assumptions)}")

    return _create_pdf_from_lines(lines)


def _create_pdf_from_lines(lines: list[str]) -> bytes:
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    commands = ["BT /F1 12 Tf 72 770 Td"]
    for line in lines:
        escaped = _escape(line)
        commands.append(f"({escaped}) Tj")
        commands.append("0 -14 Td")
    commands.append("ET")
    content_stream = "\n".join(commands).encode("latin1")

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")
    positions: list[int] = []

    def _write_obj(obj_id: int, body: bytes) -> None:
        positions.append(buffer.tell())
        buffer.write(f"{obj_id} 0 obj\n".encode("latin1"))
        buffer.write(body)
        buffer.write(b"\nendobj\n")

    _write_obj(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    _write_obj(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    _write_obj(
        3,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
    )
    content_obj = b"<< /Length %d >>\nstream\n" % len(content_stream) + content_stream + b"\nendstream"
    _write_obj(4, content_obj)
    _write_obj(5, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    xref_start = buffer.tell()
    buffer.write(b"xref\n0 6\n0000000000 65535 f \n")
    for pos in positions:
        buffer.write(f"{pos:010d} 00000 n \n".encode("latin1"))
    buffer.write(b"trailer << /Size 6 /Root 1 0 R >>\n")
    buffer.write(f"startxref {xref_start}\n%%EOF".encode("latin1"))

    return buffer.getvalue()


def register_engine() -> None:
    if REGISTRY.get(ENGINE_ID) is not None:
        return
    REGISTRY.register(
        EngineSpec(
            engine_id=ENGINE_ID,
            engine_version=ENGINE_VERSION,
            enabled_by_default=False,
            owned_tables=(),
            report_sections=(),
            routers=(router,),
            run_entrypoint=None,
        )
    )
