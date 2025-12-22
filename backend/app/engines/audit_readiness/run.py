"""
Main entrypoint for Audit Readiness Engine

Implements regulatory readiness evaluation with framework-agnostic logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.immutability import install_immutability_guards
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.engines.audit_readiness.audit_trail import AuditTrail
from backend.app.engines.audit_readiness.control_catalog import ControlCatalog, load_control_catalog
from backend.app.engines.audit_readiness.errors import (
    DatasetVersionInvalidError,
    DatasetVersionMissingError,
    DatasetVersionNotFoundError,
    RawRecordsMissingError,
    StartedAtInvalidError,
    StartedAtMissingError,
)
from backend.app.engines.audit_readiness.evidence_integration import (
    map_evidence_to_controls,
    store_control_gap_finding,
    store_regulatory_check_evidence,
)
from backend.app.engines.audit_readiness.ids import deterministic_id
from backend.app.engines.audit_readiness.models.runs import AuditReadinessRun
from backend.app.engines.audit_readiness.regulatory_logic import assess_regulatory_readiness

logger = logging.getLogger(__name__)

ENGINE_ID = "engine_audit_readiness"
ENGINE_VERSION = "v1"


def _parse_started_at(value: object) -> datetime:
    """Parse and validate started_at timestamp."""
    if value is None:
        raise StartedAtMissingError("STARTED_AT_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise StartedAtInvalidError("STARTED_AT_INVALID")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise StartedAtInvalidError("STARTED_AT_INVALID") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _validate_dataset_version_id(value: object) -> str:
    """Validate dataset_version_id parameter."""
    if value is None:
        raise DatasetVersionMissingError("DATASET_VERSION_ID_REQUIRED")
    if not isinstance(value, str) or not value.strip():
        raise DatasetVersionInvalidError("DATASET_VERSION_ID_INVALID")
    return value.strip()


async def run_engine(
    *,
    dataset_version_id: object,
    started_at: object,
    regulatory_frameworks: list[str] | None = None,
    control_catalog: dict | None = None,
    evaluation_scope: dict | None = None,
    parameters: dict | None = None,
) -> dict:
    """
    Run audit readiness evaluation engine.
    
    Args:
        dataset_version_id: Dataset version ID (required)
        started_at: ISO timestamp of evaluation start (required)
        regulatory_frameworks: List of framework IDs to evaluate (optional)
        control_catalog: Control catalog data structure (optional, from Agent 1)
        evaluation_scope: Evaluation scope parameters (optional)
        parameters: Additional runtime parameters (optional)
    
    Returns:
        Evaluation results dictionary
    """
    # Phase 0: Kill-switch gate
    if not is_engine_enabled(ENGINE_ID):
        raise RuntimeError(f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled")
    
    # Install immutability guards
    install_immutability_guards()
    
    # Phase 1: Validate inputs
    dv_id = _validate_dataset_version_id(dataset_version_id)
    started = _parse_started_at(started_at)
    frameworks = regulatory_frameworks or []
    catalog_data = control_catalog or {}
    scope = evaluation_scope or {}
    params = parameters or {}
    
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        # Validate DatasetVersion exists
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError("DATASET_VERSION_NOT_FOUND")
        
        # Phase 2: Acquire inputs
        raw_records = (await db.scalars(select(RawRecord).where(RawRecord.dataset_version_id == dv_id))).all()
        if not raw_records:
            raise RawRecordsMissingError("RAW_RECORDS_REQUIRED")
        
        source_raw_id = raw_records[0].raw_record_id
        
        # Load control catalog
        catalog = load_control_catalog(catalog_data) if catalog_data else ControlCatalog()
        
        # Initialize audit trail
        audit_trail = AuditTrail(db, dv_id)
        
        # Phase 3 & 4: Evaluate regulatory frameworks
        regulatory_results = []
        all_findings = []
        all_evidence_ids = []
        
        for framework_id in frameworks:
            try:
                # Get framework catalog
                framework_catalog = catalog.get_framework_catalog(framework_id)
                framework_name = framework_catalog.get("metadata", {}).get("name", framework_id)
                framework_version = framework_catalog.get("metadata", {}).get("version", "v1")
                
                # Map evidence to controls
                evidence_map = await map_evidence_to_controls(db, dv_id, framework_catalog)
                
                # Assess regulatory readiness
                check_result = assess_regulatory_readiness(
                    framework_id=framework_id,
                    framework_name=framework_name,
                    framework_version=framework_version,
                    dataset_version_id=dv_id,
                    control_catalog=framework_catalog,
                    evidence_map=evidence_map,
                    assessment_timestamp=started.isoformat(),
                    metadata=scope.get(framework_id, {}),
                )
                
                # Convert to dict for storage
                check_result_dict = {
                    "framework_id": check_result.framework_id,
                    "framework_name": check_result.framework_name,
                    "framework_version": check_result.framework_version,
                    "check_status": check_result.check_status,
                    "risk_level": check_result.risk_level,
                    "controls_assessed": check_result.controls_assessed,
                    "controls_passing": check_result.controls_passing,
                    "controls_failing": check_result.controls_failing,
                    "risk_score": check_result.risk_score,
                    "control_gaps": [
                        {
                            "control_id": gap.control_id,
                            "control_name": gap.control_name,
                            "gap_type": gap.gap_type,
                            "severity": gap.severity,
                            "description": gap.description,
                            "evidence_required": gap.evidence_required,
                            "remediation_guidance": gap.remediation_guidance,
                        }
                        for gap in check_result.control_gaps
                    ],
                    "evidence_ids": check_result.evidence_ids,
                }
                
                # Store regulatory check evidence
                evidence_id = await store_regulatory_check_evidence(
                    db,
                    dv_id,
                    framework_id,
                    check_result_dict,
                    started,
                )
                all_evidence_ids.append(evidence_id)
                
                # Log to audit trail
                await audit_trail.log_regulatory_check(framework_id, check_result_dict, started)
                
                # Store control gap findings
                for gap in check_result.control_gaps:
                    gap_dict = {
                        "control_id": gap.control_id,
                        "control_name": gap.control_name,
                        "gap_type": gap.gap_type,
                        "severity": gap.severity,
                        "description": gap.description,
                        "evidence_required": gap.evidence_required,
                        "remediation_guidance": gap.remediation_guidance,
                    }
                    
                    finding_id, gap_evidence_id = await store_control_gap_finding(
                        db,
                        dv_id,
                        source_raw_id,
                        framework_id,
                        gap_dict,
                        started,
                    )
                    all_findings.append(finding_id)
                    all_evidence_ids.append(gap_evidence_id)
                    
                    # Log control assessment to audit trail
                    await audit_trail.log_control_assessment(
                        framework_id,
                        gap.control_id,
                        {"gap": gap_dict, "finding_id": finding_id},
                        started,
                    )
                
                regulatory_results.append(check_result_dict)
                
            except Exception as e:
                logger.error(
                    "AUDIT_READINESS_FRAMEWORK_EVAL_FAILED framework_id=%s error=%s",
                    framework_id,
                    str(e),
                )
                # Continue with other frameworks
                regulatory_results.append({
                    "framework_id": framework_id,
                    "check_status": "error",
                    "error": str(e),
                })
        
        # Phase 7: Persist run record
        # Generate deterministic run_id from stable inputs (not timestamp)
        import hashlib
        import json
        
        stable_inputs = {
            "frameworks": sorted(frameworks),
            "scope": json.dumps(scope, sort_keys=True) if scope else "",
            "parameters": json.dumps(params, sort_keys=True) if params else "",
        }
        param_hash = hashlib.sha256(json.dumps(stable_inputs, sort_keys=True).encode()).hexdigest()[:16]
        run_id = deterministic_id(dv_id, "run", param_hash)
        
        run = AuditReadinessRun(
            run_id=run_id,
            dataset_version_id=dv_id,
            started_at=started,
            status="completed",
            regulatory_frameworks=frameworks,
            evaluation_scope=scope,
            parameters=params,
            engine_version=ENGINE_VERSION,
        )
        db.add(run)
        
        await db.commit()
        
        # Prepare response
        return {
            "dataset_version_id": dv_id,
            "run_id": run_id,
            "started_at": started.isoformat(),
            "regulatory_results": regulatory_results,
            "findings_count": len(all_findings),
            "evidence_ids": all_evidence_ids,
            "audit_trail_entries": len(audit_trail.get_entries()),
        }

