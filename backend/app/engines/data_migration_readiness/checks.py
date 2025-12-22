from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence, Tuple

from backend.app.core.dataset.raw_models import RawRecord
from backend.app.engines.data_migration_readiness.errors import ConfigurationLoadError
from backend.app.engines.data_migration_readiness.ids import deterministic_id


_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "defaults.json"


@functools.lru_cache(maxsize=1)
def load_default_config() -> Mapping[str, object]:
    try:
        raw = _CONFIG_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationLoadError("CONFIG_LOADING_FAILED") from exc
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise ConfigurationLoadError("CONFIG_INVALID_JSON") from exc
    return MappingProxyType(payload)


def _safe_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _field_has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def snapshot_raw_records(dataset_version_id: str, raw_records: Sequence[RawRecord]) -> Tuple["RawRecordSnapshot", ...]:
    snapshots: list[RawRecordSnapshot] = []
    for raw_record in sorted(raw_records, key=lambda r: r.raw_record_id):
        payload = MappingProxyType(raw_record.payload)
        snapshots.append(
            RawRecordSnapshot(
                raw_record_id=raw_record.raw_record_id,
                dataset_version_id=dataset_version_id,
                source_system=raw_record.source_system,
                source_record_id=raw_record.source_record_id,
                payload=payload,
            )
        )
    return tuple(snapshots)


def build_collection_index(records: Sequence["RawRecordSnapshot"]) -> Mapping[str, Tuple[Mapping[str, object], ...]]:
    aggregator: dict[str, list[Mapping[str, object]]] = {}
    for record in records:
        for key, value in sorted(record.payload.items()):
            if not isinstance(value, list):
                continue
            mapped_rows = []
            for entry in value:
                if isinstance(entry, dict):
                    mapped_rows.append(MappingProxyType(entry))
            if not mapped_rows:
                continue
            aggregator.setdefault(key, []).extend(mapped_rows)
    return MappingProxyType({k: tuple(v) for k, v in aggregator.items()})


@dataclass(frozen=True)
class RawRecordSnapshot:
    raw_record_id: str
    dataset_version_id: str
    source_system: str
    source_record_id: str
    payload: Mapping[str, object]


@dataclass(frozen=True)
class StructuralCheck:
    dataset_version_id: str
    required_collections: Tuple[str, ...]
    missing_collections: Tuple[str, ...]
    missing_fields: Mapping[str, Tuple[str, ...]]
    metadata_issues: Tuple[str, ...]
    compliant: bool


@dataclass(frozen=True)
class QualityCheck:
    dataset_version_id: str
    completeness_score: Decimal
    null_ratio: Decimal
    duplicate_ratio: Decimal
    per_collection: Mapping[str, Decimal]
    passes: bool
    notes: Tuple[str, ...]


@dataclass(frozen=True)
class MappingCheck:
    dataset_version_id: str
    missing_mappings: Mapping[str, Tuple[str, ...]]
    compliant: bool


@dataclass(frozen=True)
class IntegrityCheck:
    dataset_version_id: str
    record_count: int
    unique_source_records: int
    duplicate_ratio: Decimal
    compliant: bool
    notes: Tuple[str, ...]


@dataclass(frozen=True)
class RiskSignal:
    id: str
    dataset_version_id: str
    category: str
    severity: str
    description: str
    metadata: Mapping[str, object]


def evaluate_structure(
    dataset_version_id: str,
    records: Sequence[RawRecordSnapshot],
    collections: Mapping[str, Tuple[Mapping[str, object], ...]],
    config: Mapping[str, object],
) -> StructuralCheck:
    structural = config.get("structural_requirements", {})
    collection_defs = structural.get("collections", {})
    required_collections = tuple(collection_defs.keys())
    missing_collections = []
    missing_fields: dict[str, Tuple[str, ...]] = {}
    for collection_name, expected_fields in collection_defs.items():
        rows = collections.get(collection_name, ())
        if not rows:
            missing_collections.append(collection_name)
            missing_fields[collection_name] = tuple(expected_fields)
            continue
        missing = [field for field in expected_fields if not any(_field_has_value(row.get(field)) for row in rows)]
        if missing:
            missing_fields[collection_name] = tuple(missing)
    metadata_keys = tuple(structural.get("metadata_keys", []))
    present_metadata: set[str] = set()
    for snapshot in records:
        present_metadata.update(snapshot.payload.keys())
    metadata_issues = tuple(key for key in metadata_keys if key not in present_metadata)
    compliant = not missing_collections and not metadata_issues
    return StructuralCheck(
        dataset_version_id=dataset_version_id,
        required_collections=required_collections,
        missing_collections=tuple(missing_collections),
        missing_fields=MappingProxyType({k: v for k, v in missing_fields.items()}),
        metadata_issues=metadata_issues,
        compliant=compliant,
    )


def evaluate_quality(
    dataset_version_id: str,
    collections: Mapping[str, Tuple[Mapping[str, object], ...]],
    config: Mapping[str, object],
    duplicate_ratio: Decimal,
) -> QualityCheck:
    quality_config = config.get("quality_thresholds", {})
    collection_defs = (config.get("structural_requirements", {}) or {}).get("collections", {})
    total_fields = 0
    non_null_fields = 0
    null_fields = 0
    per_collection: dict[str, Decimal] = {}
    notes: list[str] = []
    for collection_name, expected_fields in collection_defs.items():
        rows = collections.get(collection_name, ())
        collection_fields = 0
        collection_non_null = 0
        if not rows:
            notes.append(f"{collection_name}: no rows received")
        for row in rows:
            for field in expected_fields:
                collection_fields += 1
                total_fields += 1
                value = row.get(field)
                if _field_has_value(value):
                    collection_non_null += 1
                    non_null_fields += 1
                else:
                    null_fields += 1
        if collection_fields:
            per_collection[collection_name] = Decimal(collection_non_null) / Decimal(collection_fields)
    if total_fields:
        completeness_score = Decimal(non_null_fields) / Decimal(total_fields)
        null_ratio = Decimal(null_fields) / Decimal(total_fields)
    else:
        completeness_score = Decimal("0")
        null_ratio = Decimal("0")
    completeness_pass = completeness_score >= _safe_decimal(quality_config.get("completeness", Decimal("1")))
    passes = completeness_pass and duplicate_ratio <= _safe_decimal(quality_config.get("duplicate_ratio", Decimal("0")))
    if null_ratio > _safe_decimal(quality_config.get("null_ratio", Decimal("1"))):
        notes.append("null ratio exceeds tolerance")
    return QualityCheck(
        dataset_version_id=dataset_version_id,
        completeness_score=completeness_score,
        null_ratio=null_ratio,
        duplicate_ratio=duplicate_ratio,
        per_collection=MappingProxyType(per_collection),
        passes=passes,
        notes=tuple(notes),
    )


def evaluate_mapping(
    dataset_version_id: str, collections: Mapping[str, Tuple[Mapping[str, object], ...]], config: Mapping[str, object]
) -> MappingCheck:
    mapping_definitions = config.get("mapping_expectations", {})
    missing_mappings: dict[str, Tuple[str, ...]] = {}
    for collection_name, expectation in mapping_definitions.items():
        field_map = expectation.get("field_mappings", {})
        rows = collections.get(collection_name, ())
        if not rows:
            missing_mappings[collection_name] = tuple(field_map.keys())
            continue
        missing_fields = [field for field in field_map if not any(field in row for row in rows)]
        if missing_fields:
            missing_mappings[collection_name] = tuple(sorted(missing_fields))
    compliant = not missing_mappings
    return MappingCheck(
        dataset_version_id=dataset_version_id,
        missing_mappings=MappingProxyType(missing_mappings),
        compliant=compliant,
    )


def verify_integrity(dataset_version_id: str, records: Sequence[RawRecordSnapshot]) -> IntegrityCheck:
    record_count = len(records)
    unique_ids = len({record.source_record_id for record in records})
    duplicate_ratio = Decimal("0")
    notes: list[str] = []
    if record_count:
        duplicates = record_count - unique_ids
        duplicate_ratio = Decimal(duplicates) / Decimal(record_count)
        if duplicates:
            notes.append(f"{duplicates} duplicate source_record_id values")
    compliant = duplicate_ratio == Decimal("0")
    return IntegrityCheck(
        dataset_version_id=dataset_version_id,
        record_count=record_count,
        unique_source_records=unique_ids,
        duplicate_ratio=duplicate_ratio,
        compliant=compliant,
        notes=tuple(notes),
    )


def assess_risks(
    dataset_version_id: str,
    *,
    structure: StructuralCheck,
    quality: QualityCheck,
    mapping: MappingCheck,
    integrity: IntegrityCheck,
    config: Mapping[str, object],
    source_systems: Sequence[str] | None = None,
) -> Tuple[RiskSignal, ...]:
    thresholds = config.get("risk_thresholds", {})
    risks: list[RiskSignal] = []
    def _make_risk(category: str, severity: str, description: str, metadata: dict[str, object]) -> None:
        payload = dict(metadata)
        if safe_source_systems:
            payload["source_systems"] = safe_source_systems
        risk = RiskSignal(
            id=deterministic_id(dataset_version_id, "risk", category, severity, description),
            dataset_version_id=dataset_version_id,
            category=category,
            severity=severity,
            description=description,
            metadata=MappingProxyType(payload),
        )
        risks.append(risk)

    safe_source_systems = tuple(sorted({s for s in (source_systems or ()) if s}))

    if not structure.compliant:
        metadata = {
            "missing_collections": structure.missing_collections,
            "metadata_issues": structure.metadata_issues,
        }
        _make_risk(
            "structure",
            "high",
            "Structural requirements not met; required collections or metadata missing.",
            metadata,
        )
    completeness = quality.completeness_score
    critical = _safe_decimal(thresholds.get("critical_completeness", Decimal("0.85")))
    warning = _safe_decimal(thresholds.get("warning_completeness", Decimal("0.90")))
    if completeness < critical:
        _make_risk(
            "quality",
            "critical",
            "Completeness score falls below the critical migration threshold.",
            {"completeness_score": float(completeness)},
        )
    elif completeness < warning:
        _make_risk(
            "quality",
            "medium",
            "Completeness score is under the warning threshold and should be addressed before migration.",
            {"completeness_score": float(completeness)},
        )
    null_threshold = _safe_decimal(thresholds.get("null_ratio", Decimal("0.10")))
    if quality.null_ratio > null_threshold:
        _make_risk(
            "quality",
            "medium",
            "Field null ratio exceeds acceptable tolerance.",
            {"null_ratio": float(quality.null_ratio)},
        )
    duplicate_threshold = _safe_decimal(thresholds.get("duplicate_ratio", Decimal("0.02")))
    if quality.duplicate_ratio > duplicate_threshold:
        _make_risk(
            "quality",
            "medium",
            "Duplicate source identifiers detected in the dataset.",
            {"duplicate_ratio": float(quality.duplicate_ratio)},
        )
    if not mapping.compliant:
        _make_risk(
            "mapping",
            "high",
            "Field mapping coverage is incomplete for one or more collections.",
            {"missing_mappings": mapping.missing_mappings},
        )
    if not integrity.compliant:
        _make_risk(
            "integrity",
            "high",
            "Data integrity violation: duplicate records would cause migration ambiguity.",
            {"duplicate_ratio": float(integrity.duplicate_ratio)},
        )
    return tuple(risks)
