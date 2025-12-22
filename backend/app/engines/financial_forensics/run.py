from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select

from backend.app.core.artifacts.fx_service import FxArtifactError, load_fx_artifact_for_dataset
from backend.app.core.db import get_sessionmaker
from backend.app.core.dataset.models import DatasetVersion
from backend.app.core.engine_registry.kill_switch import is_engine_enabled
from backend.app.engines.financial_forensics.engine import ENGINE_ID, ENGINE_VERSION
from backend.app.engines.financial_forensics.failures import RuntimeLimitError
from backend.app.engines.financial_forensics.evidence import deterministic_finding_id, emit_finding_evidence
from backend.app.engines.financial_forensics.fx_convert import convert_amount
from backend.app.engines.financial_forensics.models import FinancialForensicsRun
from backend.app.engines.financial_forensics.models.findings import FinancialForensicsFinding
from backend.app.engines.financial_forensics.models.leakage import FinancialForensicsLeakageItem
from backend.app.core.evidence.models import EvidenceRecord
from backend.app.engines.financial_forensics.matching.framework import (
    CanonicalInput,
    ConvertedAmounts,
    RuleContext,
    RuleParameters,
)
from backend.app.engines.financial_forensics.matching.orchestrator import run_matching
from backend.app.engines.financial_forensics.matching.rules_exact import (
    ExactInvoiceCreditNoteRule,
    ExactInvoicePaymentRule,
)
from backend.app.engines.financial_forensics.matching.rules_partial import (
    PartialInvoicePaymentRule,
    PartialManyInvoicesOnePaymentRule,
)
from backend.app.engines.financial_forensics.matching.rules_tolerance import (
    ToleranceInvoiceCreditNoteRule,
    ToleranceInvoicePaymentRule,
)
from backend.app.engines.financial_forensics.normalization import CanonicalRecord
from backend.app.engines.financial_forensics.review_integration import ensure_default_review_state
from backend.app.engines.financial_forensics.runtime_limits import limits_from_parameters
from backend.app.engines.financial_forensics.leakage.classifier import classify_finding
from backend.app.engines.financial_forensics.leakage.exposure import compute_finding_exposure
from backend.app.engines.financial_forensics.evidence_schema_v1 import (
    AmountComparisonEvidence,
    CounterpartyEvidence,
    DateComparisonEvidence,
    EvidenceSchemaV1,
    MatchSelectionRationale,
    PrimarySourceLinks,
    ReferenceComparisonEvidence,
    RuleIdentityEvidence,
    ToleranceEvidence,
)


class EngineDisabledError(RuntimeError):
    pass


class DatasetVersionMissingError(ValueError):
    """Raised when dataset_version_id is missing or None."""
    pass


class DatasetVersionNotFoundError(ValueError):
    """Raised when dataset_version_id is invalid or not found."""
    pass


class DatasetVersionInvalidError(ValueError):
    """Raised when dataset_version_id format is invalid."""
    pass


class FxArtifactMissingError(ValueError):
    pass


class FxArtifactInvalidError(ValueError):
    pass


def _validate_dataset_version_id(dataset_version_id: str | None) -> str:
    """
    Explicit guard: Validate dataset_version_id at function entry.
    Clear error messages for missing or invalid values.
    """
    if dataset_version_id is None:
        raise DatasetVersionMissingError(
            "DATASET_VERSION_ID_REQUIRED: dataset_version_id must be provided and cannot be None"
        )
    
    if not isinstance(dataset_version_id, str):
        raise DatasetVersionInvalidError(
            f"DATASET_VERSION_ID_INVALID_TYPE: dataset_version_id must be str, got {type(dataset_version_id).__name__}"
        )
    
    if not dataset_version_id.strip():
        raise DatasetVersionInvalidError(
            "DATASET_VERSION_ID_EMPTY: dataset_version_id cannot be empty or whitespace"
        )
    
    # Basic UUID format check (UUIDv7 should be 36 chars with hyphens)
    if len(dataset_version_id) < 32:
        raise DatasetVersionInvalidError(
            f"DATASET_VERSION_ID_INVALID_FORMAT: dataset_version_id appears malformed (length: {len(dataset_version_id)})"
        )
    
    return dataset_version_id


def _parse_started_at(started_at: str | None) -> datetime:
    if started_at is None:
        raise FxArtifactInvalidError("STARTED_AT_REQUIRED")
    if not isinstance(started_at, str) or not started_at.strip():
        raise FxArtifactInvalidError("STARTED_AT_REQUIRED")
    try:
        parsed = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FxArtifactInvalidError("STARTED_AT_INVALID_FORMAT") from exc
    if parsed.tzinfo is None:
        raise FxArtifactInvalidError("STARTED_AT_TZ_REQUIRED")
    return parsed


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


def _days_diff(a_iso: str, b_iso: str) -> int:
    a = datetime.fromisoformat(a_iso.replace("Z", "+00:00"))
    b = datetime.fromisoformat(b_iso.replace("Z", "+00:00"))
    return abs((a - b).days)


def _build_evidence_schema_v1(
    *,
    outcome_rule_id: str,
    outcome_rule_version: str,
    matched_records: list[CanonicalInput],
    invoice: CanonicalInput,
    context: RuleContext,
    tolerance_applied: Decimal | None,
    tolerance_source: str | None,
) -> EvidenceSchemaV1:
    counterparts = [r for r in matched_records if r.record_id != invoice.record_id]

    invoice_refs = list(invoice.reference_ids)
    counterpart_refs = [list(c.reference_ids) for c in counterparts]
    matched_refs = [sorted(set(invoice.reference_ids).intersection(c.reference_ids)) for c in counterparts]
    unmatched_refs = [
        sorted((set(invoice.reference_ids).union(c.reference_ids)) - set(m))
        for c, m in zip(counterparts, matched_refs, strict=False)
    ]

    # Amount comparisons (converted amounts are the comparison basis).
    invoice_amt_orig = invoice.amount_original
    counterpart_amts_orig = [c.amount_original for c in counterparts]
    sum_counterpart_orig = sum(counterpart_amts_orig, Decimal("0"))
    diff_orig = invoice_amt_orig - sum_counterpart_orig

    invoice_amt_conv = invoice.converted.amount_converted
    counterpart_amts_conv = [c.converted.amount_converted for c in counterparts]
    sum_counterpart_conv = sum(counterpart_amts_conv, Decimal("0"))
    diff_conv = invoice_amt_conv - sum_counterpart_conv

    tolerance_evidence: ToleranceEvidence | None = None
    if tolerance_applied is not None:
        tol_abs = Decimal(context.parameters.tolerance_amount) if context.parameters.tolerance_amount else None
        tol_pct = Decimal(context.parameters.tolerance_percent) if context.parameters.tolerance_percent else None
        tolerance_evidence = ToleranceEvidence(
            tolerance_absolute=tol_abs,
            tolerance_percent=tol_pct,
            threshold_applied=tolerance_applied,
            tolerance_source=tolerance_source or "run_parameters",
        )

    return EvidenceSchemaV1(
        rule_identity=RuleIdentityEvidence(
            rule_id=outcome_rule_id,
            rule_version=outcome_rule_version,
            framework_version="v1",
            executed_parameters={
                "rounding_mode": context.parameters.rounding_mode,
                "rounding_quantum": context.parameters.rounding_quantum,
                "tolerance_amount": context.parameters.tolerance_amount,
                "tolerance_percent": context.parameters.tolerance_percent,
                "max_posted_days_diff": context.parameters.max_posted_days_diff,
            },
        ),
        tolerance=tolerance_evidence,
        amount_comparison=AmountComparisonEvidence(
            invoice_amount_original=invoice_amt_orig,
            invoice_currency_original=invoice.currency_original,
            invoice_amount_converted=invoice_amt_conv,
            counterpart_amounts_original=counterpart_amts_orig,
            counterpart_currencies_original=[c.currency_original for c in counterparts],
            counterpart_amounts_converted=counterpart_amts_conv,
            sum_counterpart_amount_original=sum_counterpart_orig,
            sum_counterpart_amount_converted=sum_counterpart_conv,
            comparison_currency=invoice.converted.base_currency,
            diff_original=diff_orig,
            diff_converted=diff_conv,
        ),
        date_comparison=DateComparisonEvidence(
            invoice_posted_at=invoice.posted_at_iso,
            counterpart_posted_at=[c.posted_at_iso for c in counterparts],
            date_diffs_days=[_days_diff(invoice.posted_at_iso, c.posted_at_iso) for c in counterparts],
        ),
        reference_comparison=ReferenceComparisonEvidence(
            invoice_reference_ids=invoice_refs,
            counterpart_reference_ids=counterpart_refs,
            matched_references=matched_refs,
            unmatched_references=unmatched_refs,
        ),
        counterparty=CounterpartyEvidence(
            invoice_counterparty_id=invoice.counterparty_id,
            counterpart_counterparty_ids=[c.counterparty_id for c in counterparts],
            counterparty_match=all(c.counterparty_id == invoice.counterparty_id for c in counterparts),
            counterparty_match_logic="exact",
        ),
        match_selection=MatchSelectionRationale(
            selection_method="first_match_wins",
            selection_criteria=["amount_converted", "reference_ids", "posted_at"],
            selection_priority={"amount_converted": 1, "reference_ids": 2, "posted_at": 3},
            excluded_matches=None,
            exclusion_reasons=None,
        ),
        primary_sources=PrimarySourceLinks(
            invoice_record_id=invoice.record_id,
            counterpart_record_ids=[c.record_id for c in counterparts],
            source_system=invoice.source_system,
            source_record_ids=[invoice.source_record_id] + [c.source_record_id for c in counterparts],
            canonical_record_ids=[invoice.record_id] + [c.record_id for c in counterparts],
        ),
    )


async def run_engine(
    *,
    dataset_version_id: str | None,
    fx_artifact_id: str | None,
    started_at: str | None,
    parameters: dict,
) -> dict:
    """
    Run engine with explicit guards:
    - Kill-switch check (engine must be enabled)
    - DatasetVersion validation at entry
    - DatasetVersion existence check
    """
    # Guard 1: Kill-switch enforcement
    if not is_engine_enabled(ENGINE_ID):
        raise EngineDisabledError(
            f"ENGINE_DISABLED: Engine {ENGINE_ID} is disabled. "
            "Enable via TODISCOPE_ENABLED_ENGINES environment variable."
        )
    
    # Guard 2: Explicit dataset_version_id validation at entry
    validated_dv_id = _validate_dataset_version_id(dataset_version_id)

    if fx_artifact_id is None:
        raise FxArtifactMissingError("FX_ARTIFACT_ID_REQUIRED")
    if not isinstance(fx_artifact_id, str) or not fx_artifact_id.strip():
        raise FxArtifactMissingError("FX_ARTIFACT_ID_EMPTY")
    
    # Guard 3: DatasetVersion existence check
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        dv = await db.scalar(select(DatasetVersion).where(DatasetVersion.id == validated_dv_id))
        if dv is None:
            raise DatasetVersionNotFoundError(
                f"DATASET_VERSION_NOT_FOUND: dataset_version_id '{validated_dv_id}' does not exist. "
                "Create via ingestion API first."
            )

        try:
            _, fx_payload = await load_fx_artifact_for_dataset(
                db, fx_artifact_id=fx_artifact_id, dataset_version_id=validated_dv_id
            )
        except FxArtifactError as exc:
            raise FxArtifactInvalidError(str(exc))

        rounding_mode = parameters.get("rounding_mode")
        rounding_quantum = parameters.get("rounding_quantum")
        if not isinstance(rounding_mode, str) or not rounding_mode:
            raise FxArtifactInvalidError("ROUNDING_MODE_REQUIRED")
        if not isinstance(rounding_quantum, str) or not rounding_quantum:
            raise FxArtifactInvalidError("ROUNDING_QUANTUM_REQUIRED")

        started_at_dt = _parse_started_at(started_at)
        limits = limits_from_parameters(parameters or {})

        run_id = str(uuid.uuid4())
        run = FinancialForensicsRun(
            run_id=run_id,
            dataset_version_id=validated_dv_id,
            fx_artifact_id=fx_artifact_id,
            started_at=started_at_dt,
            status="completed",
            parameters=parameters or {},
            engine_version=ENGINE_VERSION,
        )
        db.add(run)
        await db.commit()

        canonical = (
            await db.execute(
                select(CanonicalRecord)
                .where(CanonicalRecord.dataset_version_id == validated_dv_id)
                .order_by(CanonicalRecord.record_id.asc())
            )
        ).scalars().all()

        if len(canonical) > limits.max_canonical_records:
            raise RuntimeLimitError("RUNTIME_LIMIT_EXCEEDED: max_canonical_records")

        rates: dict[str, str] = fx_payload["rates"]
        base_currency: str = fx_payload["base_currency"]
        conversions: list[dict] = []
        canonical_inputs: list[CanonicalInput] = []
        canonical_by_id: dict[str, CanonicalInput] = {}
        for rec in canonical:
            res = convert_amount(
                amount_original=Decimal(rec.amount_original),
                currency_original=rec.currency_original,
                base_currency=base_currency,
                rates=rates,
                rounding_mode=rounding_mode,
                rounding_quantum=rounding_quantum,
            )
            converted = ConvertedAmounts(
                base_currency=base_currency,
                amount_converted=res.amount_converted,
                fx_rate_used=res.fx_rate_used,
            )
            canonical_inputs.append(
                CanonicalInput(
                    record_id=rec.record_id,
                    record_type=rec.record_type,
                    source_system=rec.source_system,
                    source_record_id=rec.source_record_id,
                    posted_at_iso=_to_iso(rec.posted_at),
                    counterparty_id=rec.counterparty_id,
                    amount_original=Decimal(rec.amount_original),
                    currency_original=rec.currency_original,
                    direction=rec.direction,
                    reference_ids=tuple(sorted(str(x) for x in (rec.reference_ids or []))),
                    converted=converted,
                )
            )
            canonical_by_id[rec.record_id] = canonical_inputs[-1]
            conversions.append(
                {
                    "record_id": rec.record_id,
                    "currency_original": rec.currency_original,
                    "amount_original": str(rec.amount_original),
                    "base_currency": base_currency,
                    "amount_converted": str(res.amount_converted),
                    "fx_rate_used": str(res.fx_rate_used),
                }
            )

        rule_params = RuleParameters(
            rounding_mode=rounding_mode,
            rounding_quantum=rounding_quantum,
            tolerance_amount=parameters.get("tolerance_amount"),
            tolerance_percent=parameters.get("tolerance_percent"),
            max_posted_days_diff=parameters.get("max_posted_days_diff"),
        )
        context = RuleContext(
            dataset_version_id=validated_dv_id,
            fx_artifact_id=fx_artifact_id,
            started_at_iso=_to_iso(started_at_dt),
            parameters=rule_params,
        )

        rules = [
            ExactInvoicePaymentRule(),
            ExactInvoiceCreditNoteRule(),
        ]
        if rule_params.tolerance_amount is not None or rule_params.tolerance_percent is not None:
            rules.extend([ToleranceInvoicePaymentRule(), ToleranceInvoiceCreditNoteRule()])
        rules.append(PartialManyInvoicesOnePaymentRule())
        rules.append(PartialInvoicePaymentRule())

        outcomes, _logs = run_matching(context=context, records=tuple(canonical_inputs), rules=tuple(rules))

        findings_out: list[dict] = []
        leakage_rows: list[FinancialForensicsLeakageItem] = []
        for outcome in outcomes:
            finding_id = deterministic_finding_id(
                dataset_version_id=validated_dv_id,
                rule_id=outcome.rule_id,
                rule_version=outcome.rule_version,
                matched_record_ids=outcome.matched_record_ids,
            )

            # Build evidence schema v1 for matching (core-owned evidence registry).
            matched_records = [canonical_by_id[rid] for rid in outcome.matched_record_ids if rid in canonical_by_id]
            if not matched_records:
                continue
            # Invoice is always first record_id for our rules.
            invoice = matched_records[0]

            tolerance_applied: Decimal | None = None
            if isinstance(outcome.evidence_payload.get("tolerance"), dict):
                val = outcome.evidence_payload["tolerance"].get("computed_tolerance_in_base")
                if val is not None:
                    tolerance_applied = Decimal(str(val))

            evidence_schema = _build_evidence_schema_v1(
                outcome_rule_id=outcome.rule_id,
                outcome_rule_version=outcome.rule_version,
                matched_records=matched_records,
                invoice=invoice,
                context=context,
                tolerance_applied=tolerance_applied,
                tolerance_source="run_parameters" if tolerance_applied is not None else None,
            )
            evidence_id = await emit_finding_evidence(
                db,
                dataset_version_id=validated_dv_id,
                finding_id=finding_id,
                evidence_schema=evidence_schema,
                created_at=started_at_dt,
            )

            existing_finding = await db.scalar(
                select(FinancialForensicsFinding).where(FinancialForensicsFinding.finding_id == finding_id)
            )
            if existing_finding is None:
                finding_type = {
                    "exact": "exact_match",
                    "within_tolerance": "tolerance_match",
                    "partial": "partial_match",
                    "ambiguous": "partial_match",
                }[outcome.confidence]
                db.add(
                    FinancialForensicsFinding(
                        finding_id=finding_id,
                        run_id=run_id,
                        dataset_version_id=validated_dv_id,
                        fx_artifact_id=fx_artifact_id,
                        rule_id=outcome.rule_id,
                        rule_version=outcome.rule_version,
                        framework_version="v1",
                        finding_type=finding_type,
                        confidence=outcome.confidence,
                        matched_record_ids=list(outcome.matched_record_ids),
                        unmatched_amount=str(outcome.unmatched_amount) if outcome.unmatched_amount is not None else None,
                        primary_evidence_item_id=evidence_id,
                        evidence_ids=[evidence_id],
                        created_at=started_at_dt,
                    )
                )
                await db.flush()

            _ = await ensure_default_review_state(
                db,
                dataset_version_id=validated_dv_id,
                finding_id=finding_id,
                created_at=started_at_dt,
            )

            findings_out.append(
                {
                    "finding_id": finding_id,
                    "dataset_version_id": validated_dv_id,
                    "fx_artifact_id": fx_artifact_id,
                    "rule_id": outcome.rule_id,
                    "rule_version": outcome.rule_version,
                    "framework_version": "v1",
                    "finding_type": {
                        "exact": "exact_match",
                        "within_tolerance": "tolerance_match",
                        "partial": "partial_match",
                        "ambiguous": "partial_match",
                    }[outcome.confidence],
                    "confidence": outcome.confidence,
                    "matched_record_ids": list(outcome.matched_record_ids),
                    "unmatched_amount": str(outcome.unmatched_amount) if outcome.unmatched_amount is not None else None,
                    "primary_evidence_item_id": evidence_id,
                    "evidence_ids": [evidence_id],
                }
            )

        if len(findings_out) > limits.max_findings:
            raise RuntimeLimitError("RUNTIME_LIMIT_EXCEEDED: max_findings")

        # Persist FF-4 leakage artifacts (typology + exposure) derived from findings + evidence payloads.
        for f in findings_out:
            evidence_payload = (await db.execute(select(EvidenceRecord.payload).where(EvidenceRecord.evidence_id == f["primary_evidence_item_id"]))).scalar_one()
            exposure = compute_finding_exposure(finding=f, evidence_payload=evidence_payload)
            typ = classify_finding(finding=f, evidence_payload=evidence_payload, timing_inconsistency_days_threshold=None).typology
            leakage_rows.append(
                FinancialForensicsLeakageItem(
                    leakage_item_id=str(uuid.uuid4()),
                    run_id=run_id,
                    finding_id=f["finding_id"],
                    dataset_version_id=validated_dv_id,
                    typology=typ.value,
                    exposure_abs=exposure.exposure_abs,
                    exposure_signed=exposure.exposure_signed,
                    created_at=started_at_dt,
                )
            )
        for row in leakage_rows:
            db.add(row)
        await db.flush()

        # Deterministic response ordering
        findings_out = sorted(findings_out, key=lambda f: (f["rule_id"], f["finding_id"]))

        await db.commit()

    return {
        "run_id": run_id,
        "dataset_version_id": validated_dv_id,
        "engine_id": ENGINE_ID,
        "engine_version": ENGINE_VERSION,
        "findings": findings_out,
        "report_sections": {
            "financial_forensics_stub": {
                "status": "engine_initialized",
                "note": "Matching executed; no leakage/exposure logic executed.",
                "fx_artifact_id": fx_artifact_id,
                "converted_records": len(conversions),
            }
        },
        "conversions": conversions,
    }
