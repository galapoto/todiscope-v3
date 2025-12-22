"""Validation rules for claims consistency in the Enterprise Insurance Claim Forensics Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.engines.enterprise_insurance_claim_forensics.claims_management import (
    ClaimRecord,
    ClaimTransaction,
)
from backend.app.engines.enterprise_insurance_claim_forensics.errors import ClaimValidationError


class ClaimValidationRule:
    """Base class for claim validation rules."""

    rule_id: str
    rule_name: str
    severity: str  # "error", "warning", "info"

    def validate(self, claim: ClaimRecord, transactions: list[ClaimTransaction]) -> dict[str, Any]:
        """Validate a claim and its transactions."""
        raise NotImplementedError


class ClaimAmountConsistencyRule(ClaimValidationRule):
    """Validates that claim amount is consistent with transaction totals."""

    rule_id = "claim_amount_consistency"
    rule_name = "Claim Amount Consistency"
    severity = "error"

    def validate(self, claim: ClaimRecord, transactions: list[ClaimTransaction]) -> dict[str, Any]:
        """Check if claim amount matches transaction totals."""
        total_transactions = sum(t.amount for t in transactions if t.currency == claim.currency)
        difference = abs(claim.claim_amount - total_transactions)
        tolerance = claim.claim_amount * 0.01  # 1% tolerance

        is_valid = difference <= tolerance
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "is_valid": is_valid,
            "claim_amount": claim.claim_amount,
            "transaction_total": total_transactions,
            "difference": difference,
            "tolerance": tolerance,
            "message": (
                f"Claim amount {claim.claim_amount} {'matches' if is_valid else 'does not match'} "
                f"transaction total {total_transactions} (difference: {difference})"
            ),
        }


class ClaimDateConsistencyRule(ClaimValidationRule):
    """Validates that dates are consistent (incident date <= reported date)."""

    rule_id = "claim_date_consistency"
    rule_name = "Claim Date Consistency"
    severity = "error"

    def validate(self, claim: ClaimRecord, transactions: list[ClaimTransaction]) -> dict[str, Any]:
        """Check if dates are consistent."""
        if claim.incident_date is None:
            return {
                "rule_id": self.rule_id,
                "rule_name": self.rule_name,
                "severity": self.severity,
                "is_valid": True,
                "message": "No incident date provided, skipping date consistency check",
            }

        incident_date = claim.incident_date
        if incident_date.tzinfo is None:
            incident_date = incident_date.replace(tzinfo=timezone.utc)
        reported_date = claim.reported_date
        if reported_date.tzinfo is None:
            reported_date = reported_date.replace(tzinfo=timezone.utc)

        is_valid = incident_date <= reported_date
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "is_valid": is_valid,
            "incident_date": incident_date.isoformat(),
            "reported_date": reported_date.isoformat(),
            "message": (
                f"Incident date {incident_date.isoformat()} "
                f"{'is before or equal to' if is_valid else 'is after'} "
                f"reported date {reported_date.isoformat()}"
            ),
        }


class TransactionDateConsistencyRule(ClaimValidationRule):
    """Validates that transaction dates are within claim date range."""

    rule_id = "transaction_date_consistency"
    rule_name = "Transaction Date Consistency"
    severity = "warning"

    def validate(self, claim: ClaimRecord, transactions: list[ClaimTransaction]) -> dict[str, Any]:
        """Check if transaction dates are within reasonable range."""
        if not transactions:
            return {
                "rule_id": self.rule_id,
                "rule_name": self.rule_name,
                "severity": self.severity,
                "is_valid": True,
                "message": "No transactions to validate",
            }

        reported_date = claim.reported_date
        if reported_date.tzinfo is None:
            reported_date = reported_date.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        invalid_transactions = []

        for transaction in transactions:
            tx_date = transaction.transaction_date
            if tx_date.tzinfo is None:
                tx_date = tx_date.replace(tzinfo=timezone.utc)

            # Transaction should not be before reported date (with 30 day buffer for data entry)
            from datetime import timedelta
            min_date = reported_date - timedelta(days=30)
            # Transaction should not be in the future
            if tx_date < min_date or tx_date > now:
                invalid_transactions.append(
                    {
                        "transaction_id": transaction.transaction_id,
                        "transaction_date": tx_date.isoformat(),
                        "issue": "outside_valid_range",
                    }
                )

        is_valid = len(invalid_transactions) == 0
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "is_valid": is_valid,
            "invalid_transactions": invalid_transactions,
            "message": (
                f"Found {len(invalid_transactions)} transaction(s) with dates outside valid range"
                if not is_valid
                else "All transaction dates are within valid range"
            ),
        }


class CurrencyConsistencyRule(ClaimValidationRule):
    """Validates that all transactions use the same currency as the claim."""

    rule_id = "currency_consistency"
    rule_name = "Currency Consistency"
    severity = "error"

    def validate(self, claim: ClaimRecord, transactions: list[ClaimTransaction]) -> dict[str, Any]:
        """Check if all transactions use the same currency."""
        if not transactions:
            return {
                "rule_id": self.rule_id,
                "rule_name": self.rule_name,
                "severity": self.severity,
                "is_valid": True,
                "message": "No transactions to validate",
            }

        mismatched = [t for t in transactions if t.currency != claim.currency]
        is_valid = len(mismatched) == 0

        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "is_valid": is_valid,
            "claim_currency": claim.currency,
            "mismatched_transactions": [
                {"transaction_id": t.transaction_id, "currency": t.currency} for t in mismatched
            ],
            "message": (
                f"Found {len(mismatched)} transaction(s) with currency mismatch"
                if not is_valid
                else "All transactions use the same currency as the claim"
            ),
        }


class ClaimStatusConsistencyRule(ClaimValidationRule):
    """Validates that claim status is consistent with transaction patterns."""

    rule_id = "claim_status_consistency"
    rule_name = "Claim Status Consistency"
    severity = "warning"

    def validate(self, claim: ClaimRecord, transactions: list[ClaimTransaction]) -> dict[str, Any]:
        """Check if claim status is consistent with transactions."""
        if not transactions:
            if claim.claim_status.lower() in ("closed", "settled", "paid"):
                return {
                    "rule_id": self.rule_id,
                    "rule_name": self.rule_name,
                    "severity": self.severity,
                    "is_valid": False,
                    "message": f"Claim status is '{claim.claim_status}' but no transactions found",
                }
            return {
                "rule_id": self.rule_id,
                "rule_name": self.rule_name,
                "severity": self.severity,
                "is_valid": True,
                "message": "No transactions to validate against status",
            }

        has_payment = any(t.transaction_type.lower() in ("payment", "payout", "settlement") for t in transactions)
        status_lower = claim.claim_status.lower()

        if status_lower in ("closed", "settled", "paid") and not has_payment:
            return {
                "rule_id": self.rule_id,
                "rule_name": self.rule_name,
                "severity": self.severity,
                "is_valid": False,
                "message": f"Claim status is '{claim.claim_status}' but no payment transactions found",
            }

        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "is_valid": True,
            "message": "Claim status is consistent with transaction patterns",
        }


# Registry of all validation rules
VALIDATION_RULES: list[ClaimValidationRule] = [
    ClaimAmountConsistencyRule(),
    ClaimDateConsistencyRule(),
    TransactionDateConsistencyRule(),
    CurrencyConsistencyRule(),
    ClaimStatusConsistencyRule(),
]


def validate_claim(
    claim: ClaimRecord, transactions: list[ClaimTransaction]
) -> dict[str, Any]:
    """Run all validation rules on a claim and its transactions."""
    results = {}
    errors = []
    warnings = []

    for rule in VALIDATION_RULES:
        try:
            result = rule.validate(claim, transactions)
            results[rule.rule_id] = result

            if not result.get("is_valid", True):
                if result.get("severity") == "error":
                    errors.append(result)
                elif result.get("severity") == "warning":
                    warnings.append(result)
        except Exception as exc:
            error_result = {
                "rule_id": rule.rule_id,
                "rule_name": rule.rule_name,
                "severity": "error",
                "is_valid": False,
                "error": str(exc),
                "message": f"Validation rule '{rule.rule_name}' failed with error: {exc}",
            }
            results[rule.rule_id] = error_result
            errors.append(error_result)

    overall_valid = len(errors) == 0

    return {
        "is_valid": overall_valid,
        "errors": errors,
        "warnings": warnings,
        "rule_results": results,
        "summary": {
            "total_rules": len(VALIDATION_RULES),
            "passed": sum(1 for r in results.values() if r.get("is_valid", False)),
            "failed": len(errors),
            "warnings": len(warnings),
        },
    }


