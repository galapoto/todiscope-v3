from datetime import datetime, timezone

import pytest

from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.engines.csrd.errors import ImmutableConflictError
from backend.app.engines.csrd.run import _strict_create_evidence


@pytest.mark.anyio
async def test_strict_create_evidence_rejects_payload_change(sqlite_db) -> None:
    dv_id = "dv_test"
    started = datetime(2025, 1, 1, tzinfo=timezone.utc)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.flush()

        await _strict_create_evidence(
            db,
            evidence_id="ev1",
            dataset_version_id=dv_id,
            engine_id="engine_csrd",
            kind="report",
            payload={"assumptions": {"carbon_price": 100}},
            created_at=started,
        )

        with pytest.raises(ImmutableConflictError) as excinfo:
            await _strict_create_evidence(
                db,
                evidence_id="ev1",
                dataset_version_id=dv_id,
                engine_id="engine_csrd",
                kind="report",
                payload={"assumptions": {"carbon_price": 200}},
                created_at=started,
            )
        assert str(excinfo.value) == "IMMUTABLE_EVIDENCE_MISMATCH"


@pytest.mark.anyio
async def test_strict_create_evidence_rejects_created_at_change(sqlite_db) -> None:
    dv_id = "dv_test"
    t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(DatasetVersion(id=dv_id))
        await db.flush()

        await _strict_create_evidence(
            db,
            evidence_id="ev2",
            dataset_version_id=dv_id,
            engine_id="engine_csrd",
            kind="emissions",
            payload={"assumptions": {"unit": "tCO2e"}},
            created_at=t1,
        )

        with pytest.raises(ImmutableConflictError) as excinfo:
            await _strict_create_evidence(
                db,
                evidence_id="ev2",
                dataset_version_id=dv_id,
                engine_id="engine_csrd",
                kind="emissions",
                payload={"assumptions": {"unit": "tCO2e"}},
                created_at=t2,
            )
        assert str(excinfo.value) == "IMMUTABLE_EVIDENCE_CREATED_AT_MISMATCH"

