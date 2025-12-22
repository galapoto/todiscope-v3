from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session

from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.normalization.models import NormalizedRecord


class ImmutableViolation(RuntimeError):
    pass


ImmutabilityError = ImmutableViolation


_INSTALLED = False


def install_immutability_guards() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    @event.listens_for(Session, "before_flush")
    def _block_updates_and_deletes(session: Session, *_: object) -> None:  # noqa: ANN001
        protected = (DatasetVersion, RawRecord, NormalizedRecord, EvidenceRecord, FindingRecord, FindingEvidenceLink)

        for obj in session.deleted:
            if isinstance(obj, protected):
                raise ImmutableViolation("IMMUTABLE_DELETE")

        for obj in session.dirty:
            if isinstance(obj, protected) and session.is_modified(obj, include_collections=False):
                raise ImmutableViolation("IMMUTABLE_UPDATE")
