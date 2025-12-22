from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest

from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.service import create_dataset_version_via_ingestion
from backend.app.core.db import get_sessionmaker
from backend.app.engines.construction_cost_intelligence.compare import compare_boq_to_actuals
from backend.app.engines.construction_cost_intelligence.models import ComparisonConfig, NormalizationMapping, normalize_cost_lines
from backend.app.engines.construction_cost_intelligence.report.assembler import assemble_report
from backend.app.engines.construction_cost_intelligence.run import run_engine


@pytest.mark.anyio
async def test_reports_include_core_traceability_and_assumptions(sqlite_db: None) -> None:
    now = datetime.now(timezone.utc)

    async with get_sessionmaker()() as db:
        dv = await create_dataset_version_via_ingestion(db)
        boq_raw_id = str(uuid.uuid4())
        actual_raw_id = str(uuid.uuid4())

        db.add(
            RawRecord(
                raw_record_id=boq_raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="boq",
                payload={"lines": [{"id": "b1", "item": "A", "total": "10", "category": "labor"}]},
                ingested_at=now,
            )
        )
        db.add(
            RawRecord(
                raw_record_id=actual_raw_id,
                dataset_version_id=dv.id,
                source_system="test",
                source_record_id="actual",
                payload={
                    "lines": [
                        {"id": "a1", "item": "A", "total": "12", "category": "labor", "date_recorded": now.isoformat()},
                        {"id": "a2", "item": "C", "total": "5", "category": "materials", "date_recorded": now.isoformat()},
                    ]
                },
                ingested_at=now,
            )
        )
        await db.commit()

    core_res = await run_engine(
        dataset_version_id=dv.id,
        started_at=now.isoformat(),
        boq_raw_record_id=boq_raw_id,
        actual_raw_record_id=actual_raw_id,
        normalization_mapping={
            "line_id": "id",
            "identity": {"item_code": "item"},
            "total_cost": "total",
            "extras": ["category", "date_recorded"],
        },
        comparison_config={"identity_fields": ["item_code"], "cost_basis": "prefer_total_cost", "breakdown_fields": ["category"]},
    )
    core_traceability = core_res["traceability"]

    mapping = NormalizationMapping(line_id="id", identity={"item_code": "item"}, total_cost="total", extras=("category", "date_recorded"))
    cfg = ComparisonConfig(identity_fields=("item_code",), cost_basis="prefer_total_cost", breakdown_fields=("category",))

    boq_lines = normalize_cost_lines(
        dataset_version_id=dv.id,
        kind="boq",
        raw_lines=[{"id": "b1", "item": "A", "total": "10", "category": "labor"}],
        mapping=mapping,
    )
    actual_lines = normalize_cost_lines(
        dataset_version_id=dv.id,
        kind="actual",
        raw_lines=[
            {"id": "a1", "item": "A", "total": "12", "category": "labor", "date_recorded": now.isoformat()},
            {"id": "a2", "item": "C", "total": "5", "category": "materials", "date_recorded": now.isoformat()},
        ],
        mapping=mapping,
    )
    comparison = compare_boq_to_actuals(dataset_version_id=dv.id, boq_lines=boq_lines, actual_lines=actual_lines, config=cfg)

    async with get_sessionmaker()() as db2:
        variance_report = await assemble_report(
            db2,
            dataset_version_id=dv.id,
            run_id="run1",
            report_type="cost_variance",
            parameters={
                "comparison_result": comparison,
                "core_traceability": core_traceability,
            },
            emit_evidence=False,
        )
        time_phased_report = await assemble_report(
            db2,
            dataset_version_id=dv.id,
            run_id="run2",
            report_type="time_phased",
            parameters={
                "cost_lines": boq_lines + actual_lines,
                "period_type": "daily",
                "date_field": "date_recorded",
                "core_traceability": core_traceability,
            },
            emit_evidence=False,
        )

    for report in (variance_report, time_phased_report):
        assert report["dataset_version_id"] == dv.id
        sections = report["sections"]
        assert any(s["section_type"] == "core_traceability" for s in sections)
        core_section = next(s for s in sections if s["section_type"] == "core_traceability")
        assert core_section["assumptions_evidence_id"] == core_traceability["assumptions_evidence_id"]
        assert core_section["inputs_evidence_ids"] == core_traceability["inputs_evidence_ids"]

        lim = next(s for s in sections if s["section_type"] == "limitations_assumptions")
        assert "core" in lim["assumptions"] and "report" in lim["assumptions"]
        assert isinstance(lim["assumptions"]["core"]["assumptions"], list)

        evidence_section = next(s for s in sections if s["section_type"] == "evidence_index")
        evidence_ids = {e["evidence_id"] for e in evidence_section["evidence_index"]}
        assert core_traceability["assumptions_evidence_id"] in evidence_ids

    # Variance report must include scope creep entries flagged explicitly.
    variance_section = next(s for s in variance_report["sections"] if s["section_type"] == "cost_variances")
    scope_creep_items = [v for v in variance_section["variances"] if v.get("scope_creep") is True]
    assert scope_creep_items, "expected scope creep variances from unmatched_actual lines"
    creep = next(v for v in scope_creep_items if v["line_ids_actual"] == ["a2"])
    assert creep["severity"] == "scope_creep"
    assert creep["core_finding_ids"], "scope creep should be traceable to core findings when core_traceability is provided"
