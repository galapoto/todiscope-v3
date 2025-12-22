from __future__ import annotations

from datetime import datetime, timezone
import hashlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.artifacts.externalization_service import (
    ArtifactChecksumMismatchError,
    load_bytes_with_optional_checksum,
)
from backend.app.core.evidence.service import create_evidence, deterministic_evidence_id
from backend.app.engines.enterprise_deal_transaction_readiness.engine import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.enterprise_deal_transaction_readiness.models.findings import (
    EnterpriseDealTransactionReadinessFinding,
)


_EVIDENCE_CREATED_AT = datetime(2000, 1, 1, tzinfo=timezone.utc)


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


async def persist_finding_if_absent(
    db: AsyncSession,
    *,
    finding_id: str,
    result_set_id: str,
    dataset_version_id: str,
    kind: str,
    severity: str,
    title: str,
    detail: dict,
    evidence_id: str,
) -> EnterpriseDealTransactionReadinessFinding:
    existing = await db.scalar(
        select(EnterpriseDealTransactionReadinessFinding).where(
            EnterpriseDealTransactionReadinessFinding.finding_id == finding_id
        )
    )
    if existing is not None:
        return existing

    row = EnterpriseDealTransactionReadinessFinding(
        finding_id=finding_id,
        result_set_id=result_set_id,
        dataset_version_id=dataset_version_id,
        kind=kind,
        severity=severity,
        title=title,
        detail=detail,
        evidence_id=evidence_id,
        engine_version=ENGINE_VERSION,
    )
    db.add(row)
    await db.flush()
    return row


async def _create_evidence(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    kind: str,
    stable_key: str,
    payload: dict,
) -> str:
    evidence_id = deterministic_evidence_id(
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind=kind,
        stable_key=stable_key,
    )
    await create_evidence(
        db,
        evidence_id=evidence_id,
        dataset_version_id=dataset_version_id,
        engine_id=ENGINE_ID,
        kind=kind,
        payload=payload,
        created_at=_EVIDENCE_CREATED_AT,
    )
    return evidence_id


async def evaluate_optional_inputs_and_persist_findings(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    result_set_id: str,
    optional_inputs: dict,
    deterministic_finding_id_fn,
) -> None:
    """
    Optional inputs are non-fatal:
    - missing key -> finding
    - checksum mismatch -> finding
    - other load errors -> finding
    """
    for name, spec in sorted(optional_inputs.items()):
        stable_key = f"{result_set_id}|optional_input|{name}|{_sha256_text(spec['artifact_key'])}"
        kind: str | None = None
        detail: dict | None = None
        severity = "high"

        try:
            await load_bytes_with_optional_checksum(
                key=spec["artifact_key"],
                expected_sha256=spec.get("sha256"),
            )
        except KeyError:
            kind = "missing_prerequisite"
            detail = {
                "name": name,
                "artifact_key": spec["artifact_key"],
                "expected_sha256": spec.get("sha256"),
            }
        except ArtifactChecksumMismatchError as exc:
            kind = "prerequisite_checksum_mismatch"
            detail = {
                "name": name,
                "artifact_key": spec["artifact_key"],
                "expected_sha256": spec.get("sha256"),
                "error": str(exc),
            }
        except Exception as exc:
            kind = "prerequisite_invalid"
            detail = {
                "name": name,
                "artifact_key": spec["artifact_key"],
                "expected_sha256": spec.get("sha256"),
                "error": f"{type(exc).__name__}: {exc}",
            }

        if kind is None or detail is None:
            continue

        evidence_id = await _create_evidence(
            db,
            dataset_version_id=dataset_version_id,
            kind=kind,
            stable_key=stable_key,
            payload={
                "kind": kind,
                "result_set_id": result_set_id,
                "detail": detail,
            },
        )
        finding_id = deterministic_finding_id_fn(
            dataset_version_id=dataset_version_id,
            engine_version=ENGINE_VERSION,
            rule_id="optional_input_presence",
            rule_version="v1",
            stable_key=name,
            transaction_scope=_sha256_text(result_set_id),
        )
        await persist_finding_if_absent(
            db,
            finding_id=finding_id,
            result_set_id=result_set_id,
            dataset_version_id=dataset_version_id,
            kind=kind,
            severity=severity,
            title=f"Optional prerequisite '{name}' not satisfied",
            detail=detail,
            evidence_id=evidence_id,
        )

