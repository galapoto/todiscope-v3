from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.app.core.artifacts.externalization_service import put_bytes_immutable
from backend.app.core.metrics import engine_exports_total
from backend.app.engines.enterprise_deal_transaction_readiness.engine import ENGINE_ID
from backend.app.engines.enterprise_deal_transaction_readiness.pdf import render_simple_text_pdf


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _export_key(
    *,
    dataset_version_id: str,
    result_set_id: str,
    view_type: str,
    kind: str,
    sha256_hex: str,
    ext: str,
) -> str:
    return f"exports/{ENGINE_ID}/{dataset_version_id}/{result_set_id}/{view_type}/{kind}/{sha256_hex}.{ext}"


async def export_report_json(
    *,
    dataset_version_id: str,
    result_set_id: str,
    view_type: str,
    report_view: dict[str, Any],
) -> dict:
    data = _canonical_json_bytes(report_view)
    sha = _sha256(data)
    key = _export_key(
        dataset_version_id=dataset_version_id,
        result_set_id=result_set_id,
        view_type=view_type,
        kind="report",
        sha256_hex=sha,
        ext="json",
    )
    engine_exports_total.labels(engine_id=ENGINE_ID, format="json", view_type=view_type, status="attempt").inc()
    stored = await put_bytes_immutable(key=key, data=data, content_type="application/json")
    engine_exports_total.labels(engine_id=ENGINE_ID, format="json", view_type=view_type, status="success").inc()
    return {"format": "json", "uri": stored.uri, "sha256": stored.sha256, "size_bytes": stored.size_bytes}


async def export_report_pdf(
    *,
    dataset_version_id: str,
    result_set_id: str,
    view_type: str,
    report_view: dict[str, Any],
) -> dict:
    title = "Transaction Readiness Report"
    lines: list[str] = []
    lines.append(f"engine_id={report_view.get('engine_id')}")
    lines.append(f"dataset_version_id={report_view.get('dataset_version_id')}")
    lines.append(f"result_set_id={report_view.get('result_set_id')}")

    sections = report_view.get("sections", [])
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_id = section.get("section_id")
            if isinstance(section_id, str) and section_id:
                lines.append(f"[{section_id}]")
            if section.get("section_id") == "readiness_findings":
                finding_count = section.get("finding_count")
                if isinstance(finding_count, int):
                    lines.append(f"finding_count={finding_count}")

    pdf_bytes = render_simple_text_pdf(title=title, lines=lines)
    sha = _sha256(pdf_bytes)
    key = _export_key(
        dataset_version_id=dataset_version_id,
        result_set_id=result_set_id,
        view_type=view_type,
        kind="report",
        sha256_hex=sha,
        ext="pdf",
    )
    engine_exports_total.labels(engine_id=ENGINE_ID, format="pdf", view_type=view_type, status="attempt").inc()
    stored = await put_bytes_immutable(key=key, data=pdf_bytes, content_type="application/pdf")
    engine_exports_total.labels(engine_id=ENGINE_ID, format="pdf", view_type=view_type, status="success").inc()
    return {"format": "pdf", "uri": stored.uri, "sha256": stored.sha256, "size_bytes": stored.size_bytes}
