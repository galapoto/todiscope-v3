"""
Semantic Guards for Leakage Typology and Exposure

FF-4: Ensure no fraud/blame language, descriptive typologies, advisory exposure.
"""
from __future__ import annotations

import re
from typing import Any


class SemanticViolationError(ValueError):
    """Raised when semantic guard detects fraud/blame language or accusatory phrasing."""
    pass


# Forbidden words/phrases that imply fraud, blame, or intent
FORBIDDEN_FRAUD_WORDS = {
    "fraud",
    "fraudulent",
    "theft",
    "steal",
    "embezzlement",
    "misappropriation",
    "wrongdoing",
    "culpable",
    "guilty",
    "liable",
    "negligent",
    "negligence",
    "breach",
    "violation",
    "illegal",
    "unlawful",
    "criminal",
    "intent",
    "intentional",
    "deliberate",
    "malicious",
    "accusation",
    "accuse",
    "blame",
    "fault",
    "responsible",
    "responsibility",
    "recovery",
    "recoverable",
    "damages",
    "penalty",
    "sanction",
    "punishment",
}

# Forbidden phrases that imply decision-making or claims
FORBIDDEN_DECISION_PHRASES = {
    "must be",
    "should be",
    "is required",
    "must pay",
    "must collect",
    "is unpaid",
    "is uncollected",
    "is delinquent",
    "is overdue",
    "is outstanding",
    "is due",
    "is owed",
    "is payable",
    "is receivable",
    "has been paid",
    "has been collected",
    "has not been paid",
    "has not been collected",
}

# Allowed descriptive phrases (neutral, signal-based)
ALLOWED_DESCRIPTIVE_PHRASES = {
    "unmatched under declared rules",
    "not matched under declared constraints",
    "pattern consistent with",
    "signal indicating",
    "indicates",
    "suggests",
    "may represent",
    "could represent",
    "appears to be",
    "remains unmatched",
    "no match found",
    "partial match",
    "within tolerance",
    "exposure estimate",
    "exposure range",
    "advisory exposure",
    "estimated exposure",
    "potential exposure",
}


def validate_typology_language(leakage_type: str, description: str | None = None) -> None:
    """
    Validate that typology language is descriptive and non-accusatory.
    
    Args:
        leakage_type: Leakage type identifier
        description: Optional description text
    
    Raises:
        SemanticViolationError: If forbidden language is detected
    """
    text_to_check = f"{leakage_type} {description or ''}".lower()
    
    # Check for forbidden fraud/blame words
    for word in FORBIDDEN_FRAUD_WORDS:
        if re.search(rf"\b{word}\b", text_to_check):
            raise SemanticViolationError(
                f"SEMANTIC_VIOLATION_FRAUD_WORD: Forbidden word '{word}' detected in typology language. "
                f"Leakage typologies must be descriptive and non-accusatory."
            )
    
    # Check for forbidden decision phrases
    for phrase in FORBIDDEN_DECISION_PHRASES:
        if phrase.lower() in text_to_check:
            raise SemanticViolationError(
                f"SEMANTIC_VIOLATION_DECISION_PHRASE: Forbidden phrase '{phrase}' detected in typology language. "
                f"Leakage typologies must be advisory, not decision-making."
            )


def validate_exposure_language(exposure_basis: str) -> None:
    """
    Validate that exposure language is advisory and non-claiming.
    
    Args:
        exposure_basis: Exposure basis description
    
    Raises:
        SemanticViolationError: If forbidden language is detected
    """
    text_to_check = exposure_basis.lower()
    
    # Check for forbidden fraud/blame words
    for word in FORBIDDEN_FRAUD_WORDS:
        if re.search(rf"\b{word}\b", text_to_check):
            raise SemanticViolationError(
                f"SEMANTIC_VIOLATION_FRAUD_WORD: Forbidden word '{word}' detected in exposure language. "
                f"Exposure descriptions must be advisory and non-claiming."
            )
    
    # Check for forbidden decision phrases
    for phrase in FORBIDDEN_DECISION_PHRASES:
        if phrase.lower() in text_to_check:
            raise SemanticViolationError(
                f"SEMANTIC_VIOLATION_DECISION_PHRASE: Forbidden phrase '{phrase}' detected in exposure language. "
                f"Exposure descriptions must be advisory, not decision-making."
            )
    
    # Ensure exposure language includes advisory framing
    has_advisory_framing = any(
        phrase in text_to_check for phrase in [
            "advisory",
            "estimate",
            "estimated",
            "potential",
            "under declared",
            "under constraints",
            "based on",
            "according to",
        ]
    )
    
    if not has_advisory_framing and len(text_to_check) > 20:
        # Warn if exposure basis is long but lacks advisory framing
        # (short phrases like "unmatched amount" are acceptable)
        pass  # Allow but could add warning if needed


def validate_leakage_evidence_semantics(evidence: dict[str, Any]) -> None:
    """
    Validate that leakage evidence does not contain forbidden language.
    
    Args:
        evidence: Leakage evidence dict
    
    Raises:
        SemanticViolationError: If forbidden language is detected
    """
    # Check typology assignment
    typology = evidence.get("typology_assignment", {})
    leakage_type = typology.get("leakage_type", "")
    validate_typology_language(leakage_type)
    
    # Check exposure derivation
    exposure = evidence.get("exposure_derivation", {})
    exposure_basis = exposure.get("exposure_basis", "")
    if exposure_basis:
        validate_exposure_language(exposure_basis)
    
    # Check assignment criteria (should be descriptive)
    assignment_criteria = typology.get("assignment_criteria", [])
    for criterion in assignment_criteria:
        validate_typology_language("", criterion)


def sanitize_typology_description(description: str) -> str:
    """
    Sanitize typology description to remove any potentially accusatory language.
    
    Args:
        description: Original description
    
    Returns:
        Sanitized description
    
    Note:
        This is a defensive function. Prefer preventing violations at source.
    """
    sanitized = description
    
    # Replace forbidden phrases with neutral alternatives
    replacements = {
        "is unpaid": "remains unmatched under declared rules",
        "is uncollected": "remains unmatched under declared rules",
        "is delinquent": "pattern consistent with unmatched state",
        "is overdue": "pattern consistent with unmatched state",
        "has been paid": "matched under declared rules",
        "has not been paid": "not matched under declared rules",
        "must be": "may be",
        "should be": "could be",
    }
    
    for forbidden, replacement in replacements.items():
        sanitized = re.sub(
            rf"\b{re.escape(forbidden)}\b",
            replacement,
            sanitized,
            flags=re.IGNORECASE,
        )
    
    return sanitized


