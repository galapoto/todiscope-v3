from __future__ import annotations

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from backend.app.core.audit.models import AuditLog
from backend.app.core.calculation.models import CalculationEvidenceLink, CalculationRun
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.dataset.raw_models import RawRecord
from backend.app.core.evidence.models import EvidenceRecord, FindingEvidenceLink, FindingRecord
from backend.app.core.ingestion.models import Import
from backend.app.core.normalization.models import NormalizedRecord
from backend.app.core.reporting.models import ReportArtifact
from backend.app.core.workflows.models import WorkflowTransition


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
        protected = (
            CalculationRun,
            CalculationEvidenceLink,
            DatasetVersion,
            RawRecord,
            NormalizedRecord,
            EvidenceRecord,
            FindingRecord,
            FindingEvidenceLink,
            Import,
            AuditLog,
            ReportArtifact,
            WorkflowTransition,
        )

        for obj in session.deleted:
            if isinstance(obj, protected):
                raise ImmutableViolation("IMMUTABLE_DELETE")

        for obj in session.dirty:
            if isinstance(obj, protected) and session.is_modified(obj, include_collections=False):
                if isinstance(obj, RawRecord) and _raw_record_update_allowed(obj):
                    continue
                raise ImmutableViolation("IMMUTABLE_UPDATE")


def _raw_record_update_allowed(record: RawRecord) -> bool:
    state = inspect(record)
    changed = {attr.key for attr in state.attrs if attr.history.has_changes()}
    if not changed:
        return True
    allowed = {"file_checksum", "legacy_no_checksum"}
    if not changed.issubset(allowed):
        return False
    if "file_checksum" in changed:
        history = state.attrs.file_checksum.history
        if history.deleted and history.deleted[0] is not None:
            return False
    return True
