"""Analysis helpers for enterprise insurance claim forensics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from .claims_management import (
    ClaimRecord,
    ClaimTransaction,
    extract_transactions_from_claim_payload,
    parse_claim_from_payload,
)
from .validation import validate_claim

PAYMENT_INDICATORS = {"payment", "payout", "settlement", "reimbursement", "refund", "compensation"}
HIGH_SEVERITY_STATUSES = {"open", "pending", "escalated", "under_review"}
LOW_SEVERITY_STATUSES = {"closed", "settled", "paid", "approved"}
SEVERITY_FACTORS = {"high": 0.85, "medium": 0.55, "low": 0.35}


def extract_claims_and_transactions(
    records: Sequence[tuple[str, dict[str, Any]]], dataset_version_id: str
) -> tuple[list[ClaimRecord], list[ClaimTransaction], dict[str, str]]:
    """Build claim records, transactions, and raw record mappings from normalized inputs."""
    claims: list[ClaimRecord] = []
    transactions: list[ClaimTransaction] = []
    claim_raw_map: dict[str, str] = {}
    for raw_record_id, payload in records:
        if not isinstance(payload, dict):
            continue
        try:
            claim = parse_claim_from_payload(payload, dataset_version_id)
        except ValueError:
            continue
        claims.append(claim)
        claim_raw_map[claim.claim_id] = raw_record_id
        transactions.extend(
            extract_transactions_from_claim_payload(payload, dataset_version_id, claim.claim_id, claim.reported_date)
        )
    return claims, transactions, claim_raw_map


def group_transactions_by_claim(transactions: Sequence[ClaimTransaction]) -> dict[str, list[ClaimTransaction]]:
    grouped: dict[str, list[ClaimTransaction]] = defaultdict(list)
    for tx in transactions:
        grouped[tx.claim_id].append(tx)
    return grouped


def compute_evidence_backed_range(
    claim: ClaimRecord, transactions: Sequence[ClaimTransaction], evidence_total: float
) -> dict[str, Any]:
    """Produce a defensible amount range supported by evidence."""
    difference = abs(claim.claim_amount - evidence_total)
    tolerance = max(0.02 * max(claim.claim_amount, 1.0), difference * 0.5)
    lower = max(0.0, min(claim.claim_amount, evidence_total) - tolerance)
    upper = max(claim.claim_amount, evidence_total) + tolerance
    return {
        "lower_bound": round(lower, 2),
        "upper_bound": round(upper, 2),
        "confidence_buffer": round(tolerance, 2),
        "evidence_total": round(evidence_total, 2),
        "transaction_ids": [tx.transaction_id for tx in transactions],
    }


def _determine_severity(claim: ClaimRecord, exposure_amount: float) -> tuple[str, float]:
    status = claim.claim_status.lower()
    if exposure_amount == 0:
        return "low", SEVERITY_FACTORS["low"]
    if status in HIGH_SEVERITY_STATUSES or (claim.claim_amount > 0 and exposure_amount >= claim.claim_amount * 0.4):
        return "high", SEVERITY_FACTORS["high"]
    if status in LOW_SEVERITY_STATUSES:
        return "low", SEVERITY_FACTORS["low"]
    return "medium", SEVERITY_FACTORS["medium"]


def model_loss_exposure(claim: ClaimRecord, transactions: Sequence[ClaimTransaction]) -> dict[str, Any]:
    """Model the open loss exposure for a single claim."""
    tx_total = sum(tx.amount for tx in transactions if tx.currency == claim.currency)
    paid_total = sum(
        tx.amount
        for tx in transactions
        if tx.currency == claim.currency and tx.transaction_type.lower() in PAYMENT_INDICATORS
    )
    exposure_amount = max(claim.claim_amount - paid_total, 0.0)
    severity, severity_factor = _determine_severity(claim, exposure_amount)
    expected_loss = round(exposure_amount * severity_factor, 2)
    evidence_range = compute_evidence_backed_range(claim, transactions, tx_total)
    return {
        "claim_id": claim.claim_id,
        "policy_number": claim.policy_number,
        "claim_number": claim.claim_number,
        "claim_type": claim.claim_type,
        "claim_status": claim.claim_status,
        "claim_amount": round(claim.claim_amount, 2),
        "currency": claim.currency,
        "paid_amount": round(paid_total, 2),
        "transaction_total": round(tx_total, 2),
        "outstanding_exposure": round(exposure_amount, 2),
        "severity": severity,
        "severity_factor": severity_factor,
        "expected_loss": expected_loss,
        "evidence_range": evidence_range,
    }


def summarize_claim_portfolio(exposures: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Summarize exposures across the claim portfolio."""
    total_amount = sum(detail.get("claim_amount", 0.0) for detail in exposures)
    total_outstanding = sum(detail.get("outstanding_exposure", 0.0) for detail in exposures)
    severity_rollup: dict[str, dict[str, Any]] = {}
    for detail in exposures:
        key = detail.get("severity", "medium")
        bucket = severity_rollup.setdefault(
            key,
            {"claims": 0, "total_outstanding": 0.0, "expected_loss": 0.0},
        )
        bucket["claims"] += 1
        bucket["total_outstanding"] += detail.get("outstanding_exposure", 0.0)
        bucket["expected_loss"] += detail.get("expected_loss", 0.0)
    for bucket in severity_rollup.values():
        bucket["total_outstanding"] = round(bucket["total_outstanding"], 2)
        bucket["expected_loss"] = round(bucket["expected_loss"], 2)
    return {
        "total_claims": len(exposures),
        "total_claim_amount": round(total_amount, 2),
        "total_outstanding_exposure": round(total_outstanding, 2),
        "by_severity": severity_rollup,
        "claims": exposures,
    }


def summarize_validation_results(validation_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Aggregate validation results across claims."""
    failed_claims = [cid for cid, payload in validation_results.items() if not payload.get("is_valid", False)]
    warnings = sum(len(payload.get("warnings", ())) for payload in validation_results.values())
    errors = sum(len(payload.get("errors", ())) for payload in validation_results.values())
    return {
        "total_claims": len(validation_results),
        "failed_claims": len(failed_claims),
        "warnings": warnings,
        "errors": errors,
        "failed_claim_ids": failed_claims,
    }


def analyze_claim_portfolio(
    claims: Sequence[ClaimRecord], transactions: Sequence[ClaimTransaction]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]], dict[str, Any]]:
    """Build exposures, summary, validations, and validation summary for parsed claims."""
    grouped = group_transactions_by_claim(transactions)
    exposures = [
        model_loss_exposure(claim, grouped.get(claim.claim_id, [])) for claim in claims
    ]
    validations: dict[str, dict[str, Any]] = {}
    for claim in claims:
        validations[claim.claim_id] = validate_claim(claim, grouped.get(claim.claim_id, []))
    portfolio_summary = summarize_claim_portfolio(exposures)
    validation_summary = summarize_validation_results(validations)
    return exposures, portfolio_summary, validations, validation_summary
