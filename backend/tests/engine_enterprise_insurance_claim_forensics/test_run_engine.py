import pytest
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.evidence.models import FindingEvidenceLink, FindingRecord
from backend.app.core.evidence.service import deterministic_evidence_id
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.engines.enterprise_insurance_claim_forensics.ids import deterministic_id
from backend.app.engines.enterprise_insurance_claim_forensics.models import (
    EnterpriseInsuranceClaimForensicsFinding,
    EnterpriseInsuranceClaimForensicsRun,
)
from backend.app.engines.enterprise_insurance_claim_forensics.run import run_engine


@pytest.mark.anyio
async def test_run_engine_builds_exposures_and_findings(sqlite_db):
    dataset_version_id = "dv-insurance-forensics"
    now = datetime.now(timezone.utc)
    claim_payload = {
        "insurance_claim": {
            "claim_id": "CLAIM-123",
            "policy_number": "POL-789",
            "claim_number": "C-123",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2023-09-01T00:00:00Z",
            "incident_date": "2023-08-20T00:00:00Z",
            "claim_amount": 10000,
            "currency": "USD",
            "claimant_name": "Acme Industries",
            "claimant_type": "corporate",
            "description": "Storm damage inspection",
            "metadata": {"source": "unit-test"},
            "transactions": [
                {
                    "transaction_id": "TX-1",
                    "transaction_type": "payment",
                    "transaction_date": "2023-09-02T00:00:00Z",
                    "amount": 4000,
                    "currency": "USD",
                    "description": "Partial payment",
                },
                {
                    "transaction_id": "TX-2",
                    "transaction_type": "payment",
                    "transaction_date": "2023-09-05T00:00:00Z",
                    "amount": 2000,
                    "currency": "USD",
                    "description": "Follow-up settlement",
                },
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dataset_version_id))
        db.add(
            NormalizedRecord(
                normalized_record_id="norm-claim-1",
                dataset_version_id=dataset_version_id,
                raw_record_id="raw-claim-1",
                payload=claim_payload,
                normalized_at=now,
            )
        )
        await db.commit()

    result = await run_engine(
        dataset_version_id=dataset_version_id,
        started_at="2023-09-10T00:00:00Z",
        parameters={"assumptions": [{"name": "priority", "value": "unit"}]},
    )

    assert result["status"] == "completed"
    assert result["claim_summary"]["total_claims"] == 1
    assert result["validation_summary"]["failed_claims"] == 1

    exposures = result["loss_exposures"]
    assert len(exposures) == 1
    exposure = exposures[0]
    assert exposure["claim_id"] == "CLAIM-123"
    assert exposure["outstanding_exposure"] == 4000.0
    assert exposure["evidence_range"]["transaction_ids"] == ["TX-1", "TX-2"]

    validation_result = result["validation_results"][exposure["claim_id"]]
    assert not validation_result["is_valid"]
    assert "claim_amount_consistency" in validation_result["rule_results"]

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        run_record = await db.scalar(
            select(EnterpriseInsuranceClaimForensicsRun).where(
                EnterpriseInsuranceClaimForensicsRun.run_id == result["run_id"]
            )
        )
        assert run_record is not None
        assert run_record.dataset_version_id == dataset_version_id
        assert run_record.claim_summary["total_claim_amount"] == 10000.0
        assert "CLAIM-123" in run_record.evidence_map

        finding = await db.scalar(select(EnterpriseInsuranceClaimForensicsFinding))
        assert finding is not None
        assert finding.payload["exposure"]["claim_id"] == "CLAIM-123"

        expected_finding_id = deterministic_id(dataset_version_id, result["run_id"], "CLAIM-123", "loss_exposure")
        core_finding = await db.scalar(
            select(FindingRecord).where(FindingRecord.finding_id == expected_finding_id)
        )
        assert core_finding is not None
        assert core_finding.raw_record_id == "raw-claim-1"
        assert core_finding.payload["claim_id"] == "CLAIM-123"

        expected_evidence_id = deterministic_evidence_id(
            dataset_version_id=dataset_version_id,
            engine_id="engine_enterprise_insurance_claim_forensics",
            kind="loss_exposure",
            stable_key=f"{result['run_id']}|CLAIM-123|{expected_finding_id}",
        )
        expected_link_id = deterministic_id(dataset_version_id, result["run_id"], "CLAIM-123", "loss_exposure_link")
        link = await db.scalar(
            select(FindingEvidenceLink).where(FindingEvidenceLink.link_id == expected_link_id)
        )
        assert link is not None
        assert link.finding_id == expected_finding_id
        assert link.evidence_id == expected_evidence_id
        assert finding.evidence_ids["loss_exposure"] == [expected_evidence_id]
