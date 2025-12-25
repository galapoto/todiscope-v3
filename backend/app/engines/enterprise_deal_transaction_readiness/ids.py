"""
Deterministic ID Generation for Engine #5

All replay-stable IDs must be deterministic and derived from stable keys.
UUIDv4, randomness, and system-time-derived IDs are prohibited for replay-stable objects.

Platform Law Compliance:
- Replay Contract: Same inputs → same deterministic IDs
- All persisted outputs use deterministic IDs derived from stable keys
- Minimum stable keys: dataset_version_id, engine version, rule identifiers, 
  canonical input references, and persisted run parameters

Reference: docs/ENGINE_EXECUTION_TEMPLATE.md Phase 4
"""
from __future__ import annotations

import uuid


# Namespace UUIDs for deterministic ID generation (uuid.uuid5)
# Each namespace is unique per ID type to avoid collisions
_READINESS_FINDING_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000050")
_READINESS_PACK_MANIFEST_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000051")
_READINESS_CHECKLIST_STATUS_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-000000000052")


def deterministic_readiness_finding_id(
    *,
    dataset_version_id: str,
    engine_version: str,
    rule_id: str,
    rule_version: str,
    stable_key: str,
    transaction_scope: str,
) -> str:
    """
    Generate deterministic ID for a readiness finding.
    
    Stable keys included:
    - dataset_version_id: Immutable dataset anchor (UUIDv7)
    - engine_version: Engine version for replay compatibility
    - rule_id: Rule identifier
    - rule_version: Rule version
    - stable_key: Canonical input reference or stable identifier
    - transaction_scope: Transaction scope parameter (affects which rules apply)
    
    Platform Law #6: No implicit defaults — transaction_scope is explicit parameter
    Replay Contract: Same inputs → same finding ID
    """
    stable = f"{dataset_version_id}|{engine_version}|{rule_id}|{rule_version}|{stable_key}|{transaction_scope}"
    return str(uuid.uuid5(_READINESS_FINDING_NAMESPACE, stable))


def deterministic_readiness_pack_manifest_id(
    *,
    dataset_version_id: str,
    engine_version: str,
    transaction_scope: str,
    run_parameters_hash: str,
) -> str:
    """
    Generate deterministic ID for a readiness pack manifest.
    
    Stable keys included:
    - dataset_version_id: Immutable dataset anchor (UUIDv7)
    - engine_version: Engine version for replay compatibility
    - transaction_scope: Transaction scope parameter
    - run_parameters_hash: Deterministic hash of all run parameters that affect outputs
    
    Replay Contract: Same inputs → same manifest ID → bitwise identical manifest bytes
    """
    stable = f"{dataset_version_id}|{engine_version}|{transaction_scope}|{run_parameters_hash}"
    return str(uuid.uuid5(_READINESS_PACK_MANIFEST_NAMESPACE, stable))


def deterministic_checklist_status_id(
    *,
    dataset_version_id: str,
    engine_version: str,
    checklist_id: str,
    transaction_scope: str,
    run_parameters_hash: str,
) -> str:
    """
    Generate deterministic ID for a checklist status.
    
    Stable keys included:
    - dataset_version_id: Immutable dataset anchor (UUIDv7)
    - engine_version: Engine version for replay compatibility
    - checklist_id: Checklist identifier
    - transaction_scope: Transaction scope parameter
    - run_parameters_hash: Deterministic hash of all run parameters that affect outputs
    
    Replay Contract: Same inputs → same checklist status ID
    """
    stable = f"{dataset_version_id}|{engine_version}|{checklist_id}|{transaction_scope}|{run_parameters_hash}"
    return str(uuid.uuid5(_READINESS_CHECKLIST_STATUS_NAMESPACE, stable))


def hash_run_parameters(parameters: dict) -> str:
    """
    Generate deterministic hash of run parameters.
    
    Parameters are sorted by key to ensure deterministic hashing regardless of dict order.
    All parameters that can affect outputs must be included.
    
    Platform Law #6: No implicit defaults — all output-affecting parameters must be explicit
    Replay Contract: Same parameters → same hash → same deterministic IDs
    """
    import hashlib
    import json
    
    # Sort parameters by key for deterministic ordering
    sorted_params = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(sorted_params.encode("utf-8")).hexdigest()


def deterministic_result_set_id(
    *,
    dataset_version_id: str,
    engine_version: str,
    transaction_scope: dict,
    parameters: dict,
    optional_inputs: dict,
) -> str:
    """
    Deterministic ID for the full evaluation input set (DatasetVersion + runtime parameters).

    This is used to:
    - bind findings/manifests to an immutable input tuple
    - enable replay-stable exports (same inputs → same exported bytes)
    """
    stable_parameters = {
        "transaction_scope": transaction_scope,
        "parameters": parameters,
        "optional_inputs": optional_inputs,
    }
    run_parameters_hash = hash_run_parameters(stable_parameters)
    stable = f"{dataset_version_id}|{engine_version}|{run_parameters_hash}"
    return str(uuid.uuid5(_READINESS_PACK_MANIFEST_NAMESPACE, stable))





