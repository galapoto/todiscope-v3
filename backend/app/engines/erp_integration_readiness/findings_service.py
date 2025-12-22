"""
Findings Service for ERP Integration Readiness Engine

This service handles persistence of findings and evidence for ERP integration readiness checks.
All findings are linked to DatasetVersion for traceability.
"""
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
from backend.app.engines.erp_integration_readiness.engine import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.erp_integration_readiness.models.findings import (
    ErpIntegrationReadinessFinding,
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
) -> ErpIntegrationReadinessFinding:
    existing = await db.scalar(
        select(ErpIntegrationReadinessFinding).where(
            ErpIntegrationReadinessFinding.finding_id == finding_id
        )
    )
    if existing is not None:
        return existing

    row = ErpIntegrationReadinessFinding(
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


async def persist_readiness_findings(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    result_set_id: str,
    erp_system_id: str,
    readiness_results: dict,
    deterministic_finding_id_fn,
) -> None:
    """
    Persist findings from readiness checks.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        result_set_id: Result set ID
        erp_system_id: ERP system ID
        readiness_results: Results from readiness checks
        deterministic_finding_id_fn: Function to generate deterministic finding IDs
    """
    # Process ERP system availability findings
    availability_result = readiness_results.get("erp_system_availability", {})
    if not availability_result.get("ready", False):
        issues = availability_result.get("issues", [])
        for issue in issues:
            stable_key = f"{erp_system_id}|availability|{issue.get('field', 'unknown')}"
            evidence_id = await _create_evidence(
                db,
                dataset_version_id=dataset_version_id,
                kind="erp_system_availability_issue",
                stable_key=stable_key,
                payload={
                    "kind": "erp_system_availability_issue",
                    "result_set_id": result_set_id,
                    "erp_system_id": erp_system_id,
                    "issue": issue,
                },
            )
            finding_id = deterministic_finding_id_fn(
                dataset_version_id=dataset_version_id,
                engine_version=ENGINE_VERSION,
                rule_id="erp_system_availability",
                rule_version="v1",
                stable_key=stable_key,
                erp_system_id=erp_system_id,
            )
            await persist_finding_if_absent(
                db,
                finding_id=finding_id,
                result_set_id=result_set_id,
                dataset_version_id=dataset_version_id,
                kind="erp_system_availability_issue",
                severity=issue.get("severity", "medium"),
                title=f"ERP System Availability Issue: {issue.get('field', 'unknown')}",
                detail=issue,
                evidence_id=evidence_id,
            )
    
    # Process data integrity requirements findings
    integrity_result = readiness_results.get("data_integrity_requirements", {})
    if not integrity_result.get("ready", False):
        issues = integrity_result.get("issues", [])
        for issue in issues:
            stable_key = f"{erp_system_id}|data_integrity|{issue.get('field', 'unknown')}"
            evidence_id = await _create_evidence(
                db,
                dataset_version_id=dataset_version_id,
                kind="data_integrity_requirement_issue",
                stable_key=stable_key,
                payload={
                    "kind": "data_integrity_requirement_issue",
                    "result_set_id": result_set_id,
                    "erp_system_id": erp_system_id,
                    "issue": issue,
                },
            )
            finding_id = deterministic_finding_id_fn(
                dataset_version_id=dataset_version_id,
                engine_version=ENGINE_VERSION,
                rule_id="data_integrity_requirements",
                rule_version="v1",
                stable_key=stable_key,
                erp_system_id=erp_system_id,
            )
            await persist_finding_if_absent(
                db,
                finding_id=finding_id,
                result_set_id=result_set_id,
                dataset_version_id=dataset_version_id,
                kind="data_integrity_requirement_issue",
                severity=issue.get("severity", "medium"),
                title=f"Data Integrity Requirement Issue: {issue.get('field', 'unknown')}",
                detail=issue,
                evidence_id=evidence_id,
            )
    
    # Process operational readiness findings
    operational_result = readiness_results.get("operational_readiness", {})
    if not operational_result.get("ready", False):
        issues = operational_result.get("issues", [])
        for issue in issues:
            stable_key = f"{erp_system_id}|operational|{issue.get('field', 'unknown')}"
            evidence_id = await _create_evidence(
                db,
                dataset_version_id=dataset_version_id,
                kind="operational_readiness_issue",
                stable_key=stable_key,
                payload={
                    "kind": "operational_readiness_issue",
                    "result_set_id": result_set_id,
                    "erp_system_id": erp_system_id,
                    "issue": issue,
                },
            )
            finding_id = deterministic_finding_id_fn(
                dataset_version_id=dataset_version_id,
                engine_version=ENGINE_VERSION,
                rule_id="operational_readiness",
                rule_version="v1",
                stable_key=stable_key,
                erp_system_id=erp_system_id,
            )
            await persist_finding_if_absent(
                db,
                finding_id=finding_id,
                result_set_id=result_set_id,
                dataset_version_id=dataset_version_id,
                kind="operational_readiness_issue",
                severity=issue.get("severity", "medium"),
                title=f"Operational Readiness Issue: {issue.get('field', 'unknown')}",
                detail=issue,
                evidence_id=evidence_id,
            )


async def persist_compatibility_findings(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    result_set_id: str,
    erp_system_id: str,
    compatibility_results: dict,
    deterministic_finding_id_fn,
) -> None:
    """
    Persist findings from compatibility checks.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        result_set_id: Result set ID
        erp_system_id: ERP system ID
        compatibility_results: Results from compatibility checks
        deterministic_finding_id_fn: Function to generate deterministic finding IDs
    """
    # Process infrastructure compatibility findings
    infra_result = compatibility_results.get("infrastructure_compatibility", {})
    if not infra_result.get("compatible", False):
        issues = infra_result.get("issues", [])
        for issue in issues:
            stable_key = f"{erp_system_id}|infrastructure|{issue.get('field', 'unknown')}"
            evidence_id = await _create_evidence(
                db,
                dataset_version_id=dataset_version_id,
                kind="infrastructure_compatibility_issue",
                stable_key=stable_key,
                payload={
                    "kind": "infrastructure_compatibility_issue",
                    "result_set_id": result_set_id,
                    "erp_system_id": erp_system_id,
                    "issue": issue,
                },
            )
            finding_id = deterministic_finding_id_fn(
                dataset_version_id=dataset_version_id,
                engine_version=ENGINE_VERSION,
                rule_id="infrastructure_compatibility",
                rule_version="v1",
                stable_key=stable_key,
                erp_system_id=erp_system_id,
            )
            await persist_finding_if_absent(
                db,
                finding_id=finding_id,
                result_set_id=result_set_id,
                dataset_version_id=dataset_version_id,
                kind="infrastructure_compatibility_issue",
                severity=issue.get("severity", "medium"),
                title=f"Infrastructure Compatibility Issue: {issue.get('field', 'unknown')}",
                detail=issue,
                evidence_id=evidence_id,
            )
    
    # Process version compatibility findings
    version_result = compatibility_results.get("version_compatibility", {})
    if not version_result.get("compatible", False):
        issues = version_result.get("issues", [])
        for issue in issues:
            stable_key = f"{erp_system_id}|version|{issue.get('field', 'unknown')}"
            evidence_id = await _create_evidence(
                db,
                dataset_version_id=dataset_version_id,
                kind="version_compatibility_issue",
                stable_key=stable_key,
                payload={
                    "kind": "version_compatibility_issue",
                    "result_set_id": result_set_id,
                    "erp_system_id": erp_system_id,
                    "issue": issue,
                },
            )
            finding_id = deterministic_finding_id_fn(
                dataset_version_id=dataset_version_id,
                engine_version=ENGINE_VERSION,
                rule_id="version_compatibility",
                rule_version="v1",
                stable_key=stable_key,
                erp_system_id=erp_system_id,
            )
            await persist_finding_if_absent(
                db,
                finding_id=finding_id,
                result_set_id=result_set_id,
                dataset_version_id=dataset_version_id,
                kind="version_compatibility_issue",
                severity=issue.get("severity", "medium"),
                title=f"Version Compatibility Issue: {issue.get('field', 'unknown')}",
                detail=issue,
                evidence_id=evidence_id,
            )
    
    # Process security compatibility findings
    security_result = compatibility_results.get("security_compatibility", {})
    if not security_result.get("compatible", False):
        issues = security_result.get("issues", [])
        for issue in issues:
            stable_key = f"{erp_system_id}|security|{issue.get('field', 'unknown')}"
            evidence_id = await _create_evidence(
                db,
                dataset_version_id=dataset_version_id,
                kind="security_compatibility_issue",
                stable_key=stable_key,
                payload={
                    "kind": "security_compatibility_issue",
                    "result_set_id": result_set_id,
                    "erp_system_id": erp_system_id,
                    "issue": issue,
                },
            )
            finding_id = deterministic_finding_id_fn(
                dataset_version_id=dataset_version_id,
                engine_version=ENGINE_VERSION,
                rule_id="security_compatibility",
                rule_version="v1",
                stable_key=stable_key,
                erp_system_id=erp_system_id,
            )
            await persist_finding_if_absent(
                db,
                finding_id=finding_id,
                result_set_id=result_set_id,
                dataset_version_id=dataset_version_id,
                kind="security_compatibility_issue",
                severity=issue.get("severity", "high"),
                title=f"Security Compatibility Issue: {issue.get('field', 'unknown')}",
                detail=issue,
                evidence_id=evidence_id,
            )


async def persist_risk_assessment_findings(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    result_set_id: str,
    erp_system_id: str,
    risk_assessments: dict,
    deterministic_finding_id_fn,
) -> None:
    """
    Persist findings from risk assessments.
    
    Args:
        db: Database session
        dataset_version_id: Dataset version ID
        result_set_id: Result set ID
        erp_system_id: ERP system ID
        risk_assessments: Results from risk assessments
        deterministic_finding_id_fn: Function to generate deterministic finding IDs
    """
    # Process downtime risk
    downtime_risk = risk_assessments.get("downtime_risk", {})
    risk_level = downtime_risk.get("risk_level", "low")
    if risk_level in ("high", "critical"):
        stable_key = f"{erp_system_id}|downtime_risk"
        evidence_id = await _create_evidence(
            db,
            dataset_version_id=dataset_version_id,
            kind="downtime_risk_assessment",
            stable_key=stable_key,
            payload={
                "kind": "downtime_risk_assessment",
                "result_set_id": result_set_id,
                "erp_system_id": erp_system_id,
                "risk_assessment": downtime_risk,
            },
        )
        finding_id = deterministic_finding_id_fn(
            dataset_version_id=dataset_version_id,
            engine_version=ENGINE_VERSION,
            rule_id="downtime_risk_assessment",
            rule_version="v1",
            stable_key=stable_key,
            erp_system_id=erp_system_id,
        )
        severity = "critical" if risk_level == "critical" else "high"
        await persist_finding_if_absent(
            db,
            finding_id=finding_id,
            result_set_id=result_set_id,
            dataset_version_id=dataset_version_id,
            kind="downtime_risk_assessment",
            severity=severity,
            title=f"Downtime Risk Assessment: {risk_level.upper()} risk detected",
            detail=downtime_risk,
            evidence_id=evidence_id,
        )
    
    # Process data integrity risk
    integrity_risk = risk_assessments.get("data_integrity_risk", {})
    risk_level = integrity_risk.get("risk_level", "low")
    if risk_level in ("high", "critical"):
        stable_key = f"{erp_system_id}|data_integrity_risk"
        evidence_id = await _create_evidence(
            db,
            dataset_version_id=dataset_version_id,
            kind="data_integrity_risk_assessment",
            stable_key=stable_key,
            payload={
                "kind": "data_integrity_risk_assessment",
                "result_set_id": result_set_id,
                "erp_system_id": erp_system_id,
                "risk_assessment": integrity_risk,
            },
        )
        finding_id = deterministic_finding_id_fn(
            dataset_version_id=dataset_version_id,
            engine_version=ENGINE_VERSION,
            rule_id="data_integrity_risk_assessment",
            rule_version="v1",
            stable_key=stable_key,
            erp_system_id=erp_system_id,
        )
        severity = "critical" if risk_level == "critical" else "high"
        await persist_finding_if_absent(
            db,
            finding_id=finding_id,
            result_set_id=result_set_id,
            dataset_version_id=dataset_version_id,
            kind="data_integrity_risk_assessment",
            severity=severity,
            title=f"Data Integrity Risk Assessment: {risk_level.upper()} risk detected",
            detail=integrity_risk,
            evidence_id=evidence_id,
        )
    
    # Process compatibility risk
    compat_risk = risk_assessments.get("compatibility_risk", {})
    risk_level = compat_risk.get("risk_level", "low")
    if risk_level in ("high", "critical"):
        stable_key = f"{erp_system_id}|compatibility_risk"
        evidence_id = await _create_evidence(
            db,
            dataset_version_id=dataset_version_id,
            kind="compatibility_risk_assessment",
            stable_key=stable_key,
            payload={
                "kind": "compatibility_risk_assessment",
                "result_set_id": result_set_id,
                "erp_system_id": erp_system_id,
                "risk_assessment": compat_risk,
            },
        )
        finding_id = deterministic_finding_id_fn(
            dataset_version_id=dataset_version_id,
            engine_version=ENGINE_VERSION,
            rule_id="compatibility_risk_assessment",
            rule_version="v1",
            stable_key=stable_key,
            erp_system_id=erp_system_id,
        )
        severity = "critical" if risk_level == "critical" else "high"
        await persist_finding_if_absent(
            db,
            finding_id=finding_id,
            result_set_id=result_set_id,
            dataset_version_id=dataset_version_id,
            kind="compatibility_risk_assessment",
            severity=severity,
            title=f"Compatibility Risk Assessment: {risk_level.upper()} risk detected",
            detail=compat_risk,
            evidence_id=evidence_id,
        )


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
            erp_system_id=_sha256_text(result_set_id),
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


