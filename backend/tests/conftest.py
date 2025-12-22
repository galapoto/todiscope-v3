import os
import tempfile

import pytest
import pytest_asyncio

from backend.app.core.artifacts.store import reset_artifact_store_for_tests
from backend.app.core.db import get_engine, reset_db_state_for_tests
from backend.app.core.engine_registry.registry import REGISTRY
from backend.app.core.governance import models as _governance  # noqa: F401
from backend.db.models.base import Base
from sqlalchemy import create_engine


@pytest.fixture(autouse=True)
def _reset_globals_and_env() -> None:
    os.environ.pop("TODISCOPE_DATABASE_URL", None)
    os.environ.pop("TODISCOPE_ARTIFACT_STORE_KIND", None)
    os.environ.pop("TODISCOPE_ENABLED_ENGINES", None)
    os.environ.pop("TODISCOPE_S3_ENDPOINT_URL", None)
    os.environ.pop("TODISCOPE_S3_ACCESS_KEY_ID", None)
    os.environ.pop("TODISCOPE_S3_SECRET_ACCESS_KEY", None)
    os.environ.pop("TODISCOPE_S3_BUCKET", None)
    os.environ.pop("TODISCOPE_API_KEYS", None)

    reset_artifact_store_for_tests()
    reset_db_state_for_tests()
    REGISTRY.reset_for_tests()


@pytest_asyncio.fixture
async def sqlite_db() -> None:
    tmp = tempfile.NamedTemporaryFile(prefix="todiscope-test-", suffix=".db", delete=False)
    tmp.close()
    db_url = f"sqlite+aiosqlite:///{tmp.name}"
    os.environ["TODISCOPE_DATABASE_URL"] = db_url
    sync_engine = create_engine(f"sqlite:///{tmp.name}")
    from backend.app.core.artifacts import fx_models as _fx  # noqa: F401
    from backend.app.core.evidence import models as _evidence  # noqa: F401
    from backend.app.core.review import models as _review  # noqa: F401
    from backend.app.core.dataset import raw_models as _raw  # noqa: F401
    from backend.app.core.normalization import models as _norm_core  # noqa: F401
    from backend.app.core.governance import models as _governance  # noqa: F401
    from backend.app.engines.financial_forensics import models as _  # noqa: F401
    from backend.app.engines.enterprise_deal_transaction_readiness import models as _engine5  # noqa: F401
    from backend.app.engines.financial_forensics import normalization as _norm  # noqa: F401
    from backend.app.engines.financial_forensics.models import findings as _findings  # noqa: F401
    from backend.app.engines.financial_forensics.models import leakage as _leakage  # noqa: F401
    from backend.app.engines.data_migration_readiness import models as _data_migration_models  # noqa: F401
    from backend.app.engines.enterprise_litigation_dispute import models as _litigation_models  # noqa: F401
    from backend.app.engines.regulatory_readiness import models as _regulatory_models  # noqa: F401
    from backend.app.engines.enterprise_insurance_claim_forensics import models as _insurance_claim_models  # noqa: F401
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    engine = get_engine()
    try:
        yield None
    finally:
        await engine.dispose()
        os.unlink(tmp.name)
