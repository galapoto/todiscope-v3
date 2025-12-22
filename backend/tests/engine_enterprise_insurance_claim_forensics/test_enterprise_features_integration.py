"""Integration tests for enterprise features: readiness scores, remediation tasks, and review workflow."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import pytest
from sqlalchemy import select

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.dataset.uuidv7 import uuid7
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.review.models import ReviewItem
from backend.app.engines.enterprise_insurance_claim_forensics.run import run_engine


@pytest.mark.anyio
async def test_readiness_scores_in_engine_output(sqlite_db: None) -> None:
    """Test that readiness scores are included in engine output."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-readiness-test",
            "policy_number": "POL-READINESS",
            "claim_number": "CLM-READINESS",
            "claim_type": "property",
            "claim_status": "closed",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2023-12-15T00:00:00Z",
            "claim_amount": 10000.0,
            "currency": "USD",
            "claimant_name": "Readiness Test",
            "claimant_type": "individual",
            "description": "Readiness test claim",
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "transaction_type": "payment",
                    "transaction_date": "2024-01-15T00:00:00Z",
                    "amount": 10000.0,
                    "currency": "USD",
                    "description": "Full payment",
                }
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-READINESS",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    result = await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    # Verify readiness scores are in output
    assert "readiness_scores" in result
    readiness_scores = result["readiness_scores"]
    assert "portfolio_readiness_score" in readiness_scores
    assert "portfolio_readiness_level" in readiness_scores
    assert "claim_scores" in readiness_scores
    assert "distribution" in readiness_scores
    
    # Verify portfolio score is valid
    assert 0.0 <= readiness_scores["portfolio_readiness_score"] <= 100.0
    assert readiness_scores["portfolio_readiness_level"] in ("excellent", "good", "adequate", "weak")
    
    # Verify claim-level scores exist
    assert len(readiness_scores["claim_scores"]) > 0
    for claim_id, score_data in readiness_scores["claim_scores"].items():
        assert "readiness_score" in score_data
        assert "readiness_level" in score_data
        assert "component_scores" in score_data


@pytest.mark.anyio
async def test_remediation_tasks_in_engine_output(sqlite_db: None) -> None:
    """Test that remediation tasks are included in engine output."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-remediation-test",
            "policy_number": "POL-REMEDIATION",
            "claim_number": "CLM-REMEDIATION",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2024-01-15T00:00:00Z",  # After reported date - invalid
            "claim_amount": 10000.0,
            "currency": "USD",
            "claimant_name": "Remediation Test",
            "claimant_type": "individual",
            "description": "Remediation test claim",
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "transaction_type": "payment",
                    "transaction_date": "2024-01-15T00:00:00Z",
                    "amount": 5000.0,  # Mismatched amount
                    "currency": "EUR",  # Mismatched currency
                    "description": "Partial payment",
                }
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-REMEDIATION",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    result = await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    # Verify remediation tasks are in output
    assert "remediation_tasks" in result
    tasks = result["remediation_tasks"]
    assert isinstance(tasks, list)
    assert len(tasks) > 0
    
    # Verify task structure
    for task in tasks:
        assert "id" in task
        assert "category" in task
        assert "severity" in task
        assert "description" in task
        assert "details" in task
        assert "status" in task
        assert task["severity"] in ("high", "medium", "low")
        assert task["status"] in ("pending", "completed")
        assert task["category"] in ("validation", "exposure", "data_quality", "monitoring")


@pytest.mark.anyio
async def test_review_items_created_for_findings(sqlite_db: None) -> None:
    """Test that review items are created for findings requiring review."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-review-test",
            "policy_number": "POL-REVIEW",
            "claim_number": "CLM-REVIEW",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2023-12-15T00:00:00Z",
            "claim_amount": 10000.0,
            "currency": "USD",
            "claimant_name": "Review Test",
            "claimant_type": "individual",
            "description": "Review test claim",
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "transaction_type": "payment",
                    "transaction_date": "2024-01-15T00:00:00Z",
                    "amount": 5000.0,
                    "currency": "USD",
                    "description": "Partial payment",
                }
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-REVIEW",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    # Verify review items were created
    async with sessionmaker() as db:
        review_items = (
            await db.scalars(
                select(ReviewItem).where(
                    ReviewItem.dataset_version_id == dv_id,
                    ReviewItem.engine_id == "engine_enterprise_insurance_claim_forensics",
                    ReviewItem.subject_type == "finding",
                )
            )
        ).all()
        
        assert len(review_items) > 0
        
        for review_item in review_items:
            assert review_item.dataset_version_id == dv_id
            assert review_item.engine_id == "engine_enterprise_insurance_claim_forensics"
            assert review_item.subject_type == "finding"
            assert review_item.state == "unreviewed"
            assert review_item.subject_id is not None


@pytest.mark.anyio
async def test_end_to_end_enterprise_features(sqlite_db: None) -> None:
    """End-to-end test of all enterprise features working together."""
    dv_id = str(uuid7())
    raw_id = f"raw-{uuid.uuid4().hex}"
    claim_payload = {
        "insurance_claim": {
            "claim_id": "claim-e2e-enterprise",
            "policy_number": "POL-E2E",
            "claim_number": "CLM-E2E",
            "claim_type": "property",
            "claim_status": "open",
            "reported_date": "2024-01-01T00:00:00Z",
            "incident_date": "2023-12-15T00:00:00Z",
            "claim_amount": 50000.0,
            "currency": "USD",
            "claimant_name": "E2E Enterprise Test",
            "claimant_type": "individual",
            "description": "End-to-end enterprise features test",
            "transactions": [
                {
                    "transaction_id": "tx-1",
                    "transaction_type": "payment",
                    "transaction_date": "2024-01-15T00:00:00Z",
                    "amount": 20000.0,
                    "currency": "USD",
                    "description": "Partial payment",
                }
            ],
        }
    }

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        db.add(
            RawRecord(
                raw_record_id=raw_id,
                dataset_version_id=dv_id,
                source_system="insurance",
                source_record_id="INS-E2E",
                payload=claim_payload,
                ingested_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            NormalizedRecord(
                normalized_record_id=f"norm-{uuid.uuid4().hex}",
                dataset_version_id=dv_id,
                raw_record_id=raw_id,
                payload=claim_payload,
                normalized_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    result = await run_engine(
        dataset_version_id=dv_id,
        started_at="2024-01-01T00:00:00Z",
        parameters={},
    )

    # Verify all enterprise features are present
    assert "readiness_scores" in result
    assert "remediation_tasks" in result
    
    # Verify readiness scores
    readiness_scores = result["readiness_scores"]
    assert readiness_scores["portfolio_readiness_score"] >= 0.0
    assert readiness_scores["portfolio_readiness_score"] <= 100.0
    
    # Verify remediation tasks
    tasks = result["remediation_tasks"]
    assert len(tasks) > 0
    
    # Verify review items were created
    async with sessionmaker() as db:
        review_items = (
            await db.scalars(
                select(ReviewItem).where(
                    ReviewItem.dataset_version_id == dv_id,
                    ReviewItem.engine_id == "engine_enterprise_insurance_claim_forensics",
                )
            )
        ).all()
        
        assert len(review_items) > 0


