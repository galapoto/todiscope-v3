"""
Core normalization workflow service.

Provides explicit normalization workflow with preview, validation, and commit steps.
Engines can propose normalization rules, but the core orchestrates the workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import load_raw_records
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.normalization.pipeline import normalize_payload
from backend.app.core.normalization.warnings import (
    NormalizationWarning,
    WarningSeverity,
    create_data_quality_warning,
    create_fuzzy_match_warning,
    create_missing_value_warning,
    create_unit_discrepancy_warning,
)


# Type alias for engine normalization functions
NormalizationRule = Callable[[dict[str, Any], str], tuple[dict[str, Any], list[NormalizationWarning]]]


@dataclass(frozen=True, slots=True)
class NormalizationPreview:
    """
    Preview of normalization results before committing.
    
    Attributes:
        dataset_version_id: DatasetVersion ID
        total_records: Total number of records to normalize
        preview_records: List of preview records (first N records)
        warnings: List of warnings generated during normalization
        warnings_by_severity: Count of warnings by severity
    """

    dataset_version_id: str
    total_records: int
    preview_records: list[dict[str, Any]]
    warnings: list[NormalizationWarning]
    warnings_by_severity: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Convert preview to dictionary for serialization."""
        return {
            "dataset_version_id": self.dataset_version_id,
            "total_records": self.total_records,
            "preview_records": self.preview_records,
            "warnings": [w.to_dict() for w in self.warnings],
            "warnings_by_severity": self.warnings_by_severity,
        }


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """
    Result of normalization commit operation.
    
    Attributes:
        dataset_version_id: DatasetVersion ID
        records_normalized: Number of records normalized
        records_skipped: Number of records skipped (due to errors)
        warnings: List of warnings generated
        normalized_record_ids: List of normalized record IDs created
    """

    source_dataset_version_id: str
    normalized_dataset_version_id: str
    records_normalized: int
    records_skipped: int
    warnings: list[NormalizationWarning]
    normalized_record_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "source_dataset_version_id": self.source_dataset_version_id,
            "normalized_dataset_version_id": self.normalized_dataset_version_id,
            "records_normalized": self.records_normalized,
            "records_skipped": self.records_skipped,
            "warnings": [w.to_dict() for w in self.warnings],
            "normalized_record_ids": self.normalized_record_ids,
        }


async def preview_normalization(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    normalization_rule: NormalizationRule | None = None,
    preview_limit: int = 10,
    verify_checksums: bool = True,
    strict_mode: bool = True,
) -> NormalizationPreview:
    """
    Preview normalization results without committing.
    
    This function loads raw records, applies normalization rules, and returns
    a preview with warnings. No data is persisted to the database.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID to normalize
        normalization_rule: Optional engine-specific normalization rule
        preview_limit: Maximum number of records to include in preview
        verify_checksums: Whether to verify checksums on read
        strict_mode: Whether to use strict mode for checksum verification
    
    Returns:
        NormalizationPreview with preview records and warnings
    """
    # Load raw records
    raw_records = await load_raw_records(
        db,
        dataset_version_id=dataset_version_id,
        verify_checksums=verify_checksums,
        strict_mode=strict_mode,
        order_by=(RawRecord.ingested_at.asc(), RawRecord.raw_record_id.asc()),
    )

    if not raw_records:
        return NormalizationPreview(
            dataset_version_id=dataset_version_id,
            total_records=0,
            preview_records=[],
            warnings=[],
            warnings_by_severity={},
        )

    # Apply normalization and collect warnings
    preview_records: list[dict[str, Any]] = []
    all_warnings: list[NormalizationWarning] = []

    for raw_record in raw_records[:preview_limit]:
        try:
            if normalization_rule:
                # Use engine-specific normalization rule
                normalized_payload, warnings = normalization_rule(
                    raw_record.payload, dataset_version_id
                )
                warnings = warnings + _generate_core_warnings(raw_record)
            else:
                # Use core normalization (basic key normalization)
                normalized_payload = normalize_payload(raw_record.payload)  # type: ignore[arg-type]
                warnings = _generate_core_warnings(raw_record)

            preview_records.append({
                "raw_record_id": raw_record.raw_record_id,
                "source_system": raw_record.source_system,
                "source_record_id": raw_record.source_record_id,
                "raw_payload": raw_record.payload,
                "normalized_payload": normalized_payload,
            })
            all_warnings.extend(warnings)
        except Exception as e:
            # Generate error warning for failed normalization
            all_warnings.append(
                create_data_quality_warning(
                    raw_record_id=raw_record.raw_record_id,
                    code="NORMALIZATION_ERROR",
                    message=f"Normalization failed: {str(e)}",
                    affected_fields=[],
                    explanation=f"An error occurred during normalization: {str(e)}",
                    recommendation="Review the raw record data and normalization rules.",
                    severity=WarningSeverity.ERROR,
                )
            )

    # Count warnings by severity
    warnings_by_severity: dict[str, int] = {}
    for severity in WarningSeverity:
        count = sum(1 for w in all_warnings if w.severity == severity)
        if count > 0:
            warnings_by_severity[severity.value] = count

    return NormalizationPreview(
        dataset_version_id=dataset_version_id,
        total_records=len(raw_records),
        preview_records=preview_records,
        warnings=all_warnings,
        warnings_by_severity=warnings_by_severity,
    )


async def validate_normalization(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    normalization_rule: NormalizationRule | None = None,
    verify_checksums: bool = True,
    strict_mode: bool = True,
) -> tuple[bool, list[NormalizationWarning]]:
    """
    Validate normalization rules without committing.
    
    This function validates that normalization rules can be applied to all
    records without critical errors. Returns validation status and warnings.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID to validate
        normalization_rule: Optional engine-specific normalization rule
        verify_checksums: Whether to verify checksums on read
        strict_mode: Whether to use strict mode for checksum verification
    
    Returns:
        Tuple of (is_valid, warnings) where is_valid is True if no critical errors
    """
    # Load all raw records
    raw_records = await load_raw_records(
        db,
        dataset_version_id=dataset_version_id,
        verify_checksums=verify_checksums,
        strict_mode=strict_mode,
        order_by=(RawRecord.ingested_at.asc(), RawRecord.raw_record_id.asc()),
    )

    all_warnings: list[NormalizationWarning] = []
    has_critical_errors = False

    for raw_record in raw_records:
        try:
            if normalization_rule:
                _, warnings = normalization_rule(raw_record.payload, dataset_version_id)
                warnings = warnings + _generate_core_warnings(raw_record)
            else:
                normalize_payload(raw_record.payload)  # type: ignore[arg-type]
                warnings = _generate_core_warnings(raw_record)

            all_warnings.extend(warnings)
            
            # Check for critical errors
            if any(w.severity == WarningSeverity.CRITICAL or w.severity == WarningSeverity.ERROR for w in warnings):
                has_critical_errors = True
        except Exception:
            has_critical_errors = True
            all_warnings.append(
                create_data_quality_warning(
                    raw_record_id=raw_record.raw_record_id,
                    code="NORMALIZATION_ERROR",
                    message="Normalization validation failed",
                    affected_fields=[],
                    explanation="An error occurred during normalization validation.",
                    recommendation="Review the raw record data and normalization rules.",
                    severity=WarningSeverity.ERROR,
                )
            )

    return (not has_critical_errors, all_warnings)


async def commit_normalization(
    db: AsyncSession,
    *,
    dataset_version_id: str,
    normalization_rule: NormalizationRule | None = None,
    verify_checksums: bool = True,
    strict_mode: bool = True,
    skip_on_error: bool = False,
) -> NormalizationResult:
    """
    Commit normalization to database.
    
    This function normalizes all raw records and persists NormalizedRecord instances.
    Warnings are collected but do not prevent normalization unless skip_on_error=False
    and critical errors occur.
    
    Args:
        db: Database session
        dataset_version_id: DatasetVersion ID to normalize
        normalization_rule: Optional engine-specific normalization rule
        verify_checksums: Whether to verify checksums on read
        strict_mode: Whether to use strict mode for checksum verification
        skip_on_error: Whether to skip records with errors (True) or fail (False)
    
    Returns:
        NormalizationResult with normalization statistics
    """
    # Load raw records
    raw_records = await load_raw_records(
        db,
        dataset_version_id=dataset_version_id,
        verify_checksums=verify_checksums,
        strict_mode=strict_mode,
        order_by=(RawRecord.ingested_at.asc(), RawRecord.raw_record_id.asc()),
    )

    if not raw_records:
        return NormalizationResult(
            source_dataset_version_id=dataset_version_id,
            normalized_dataset_version_id=dataset_version_id,
            records_normalized=0,
            records_skipped=0,
            warnings=[],
            normalized_record_ids=[],
        )

    # Normalization is committed to the same DatasetVersion. Lifecycle enforcement
    # (Import → Normalize → Calculate → Report → Audit) is keyed by dataset_version_id,
    # and engine endpoints require normalization completion for the same dataset version.
    normalized_dataset_version_id = dataset_version_id

    now = datetime.now(timezone.utc)
    normalized_count = 0
    skipped_count = 0
    all_warnings: list[NormalizationWarning] = []
    normalized_record_ids: list[str] = []

    for raw_record in raw_records:
        try:
            if normalization_rule:
                normalized_payload, warnings = normalization_rule(
                    raw_record.payload, dataset_version_id
                )
                warnings = warnings + _generate_core_warnings(raw_record)
            else:
                normalized_payload = normalize_payload(raw_record.payload)  # type: ignore[arg-type]
                warnings = _generate_core_warnings(raw_record)

            all_warnings.extend(warnings)

            # Check for critical errors
            has_critical = any(
                w.severity == WarningSeverity.CRITICAL or w.severity == WarningSeverity.ERROR
                for w in warnings
            )

            if has_critical and not skip_on_error:
                raise ValueError(f"Critical normalization error for record {raw_record.raw_record_id}")

            # Create NormalizedRecord
            normalized_record_id = str(uuid.uuid4())
            normalized_record = NormalizedRecord(
                normalized_record_id=normalized_record_id,
                dataset_version_id=normalized_dataset_version_id,
                raw_record_id=raw_record.raw_record_id,
                payload=normalized_payload,  # type: ignore[arg-type]
                normalized_at=now,
            )
            db.add(normalized_record)
            normalized_record_ids.append(normalized_record_id)
            normalized_count += 1

        except Exception as e:
            if skip_on_error:
                skipped_count += 1
                all_warnings.append(
                    create_data_quality_warning(
                        raw_record_id=raw_record.raw_record_id,
                        code="NORMALIZATION_ERROR",
                        message=f"Normalization failed: {str(e)}",
                        affected_fields=[],
                        explanation=f"An error occurred during normalization: {str(e)}",
                        recommendation="Review the raw record data and normalization rules.",
                        severity=WarningSeverity.ERROR,
                    )
                )
            else:
                raise

    await db.commit()
    
    # Record normalization completion in workflow state machine (authoritative source)
    from backend.app.core.lifecycle.enforcement import record_normalize_completion
    await record_normalize_completion(
        db,
        dataset_version_id=normalized_dataset_version_id,
        actor_id=None,  # System-initiated
    )

    return NormalizationResult(
        source_dataset_version_id=dataset_version_id,
        normalized_dataset_version_id=normalized_dataset_version_id,
        records_normalized=normalized_count,
        records_skipped=skipped_count,
        warnings=all_warnings,
        normalized_record_ids=normalized_record_ids,
    )


def _generate_core_warnings(raw_record: RawRecord) -> list[NormalizationWarning]:
    """Generate core warnings for basic normalization issues."""
    warnings: list[NormalizationWarning] = []

    # Check for missing required fields
    required_fields = ["source_system", "source_record_id"]
    for field in required_fields:
        if field not in raw_record.payload or not raw_record.payload.get(field):
            warnings.append(
                create_missing_value_warning(
                    raw_record_id=raw_record.raw_record_id,
                    field_name=field,
                )
            )

    # Fuzzy field name hints (heuristic).
    field_names = [str(k) for k in raw_record.payload.keys()]
    for i, left in enumerate(field_names):
        for right in field_names[i + 1 :]:
            if left == right:
                continue
            ratio = _similarity_ratio(left, right)
            if ratio >= 0.9:
                warnings.append(
                    create_fuzzy_match_warning(
                        raw_record_id=raw_record.raw_record_id,
                        field_name=left,
                        original_value=left,
                        suggested_value=right,
                        confidence=ratio,
                    )
                )

    # Unit conversion warnings (heuristic: numeric value without unit/currency field).
    unit_fields = {k for k in field_names if "unit" in k.lower() or "currency" in k.lower()}
    for key, value in raw_record.payload.items():
        if isinstance(value, (int, float)) and ("amount" in str(key).lower() or "value" in str(key).lower()):
            if not unit_fields:
                warnings.append(
                    create_unit_discrepancy_warning(
                        raw_record_id=raw_record.raw_record_id,
                        field_name=str(key),
                        detected_unit="missing",
                        expected_unit=None,
                    )
                )

    return warnings


def _similarity_ratio(left: str, right: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, left, right).ratio()
