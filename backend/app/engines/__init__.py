def register_all_engines() -> None:
    # Engines register themselves with the core registry on import.
    # Keep this explicit and minimal; core must never import engines.
    from backend.app.engines.financial_forensics.engine import register_engine as _register_financial_forensics
    from backend.app.engines.audit_readiness.engine import register_engine as _register_audit_readiness
    from backend.app.engines.enterprise_deal_transaction_readiness.engine import register_engine as _register_enterprise_deal_transaction_readiness
    from backend.app.engines.enterprise_capital_debt_readiness.engine import (
        register_engine as _register_enterprise_capital_debt_readiness,
    )
    from backend.app.engines.enterprise_distressed_asset_debt_stress.engine import (
        register_engine as _register_distressed_asset_debt_stress,
    )
    from backend.app.engines.enterprise_insurance_claim_forensics.engine import (
        register_engine as _register_enterprise_insurance_claim_forensics,
    )
    from backend.app.engines.csrd.engine import register_engine as _register_csrd
    from backend.app.engines.construction_cost_intelligence.engine import register_engine as _register_construction_cost_intelligence
    from backend.app.engines.erp_integration_readiness.engine import register_engine as _register_erp_integration_readiness
    from backend.app.engines.enterprise_litigation_dispute.engine import register_engine as _register_enterprise_litigation_dispute
    from backend.app.engines.data_migration_readiness.engine import register_engine as _register_data_migration_readiness
    from backend.app.engines.regulatory_readiness.engine import register_engine as _register_regulatory_readiness

    _register_financial_forensics()
    _register_audit_readiness()
    _register_enterprise_deal_transaction_readiness()
    _register_enterprise_capital_debt_readiness()
    _register_distressed_asset_debt_stress()
    _register_enterprise_insurance_claim_forensics()
    _register_csrd()
    _register_construction_cost_intelligence()
    _register_erp_integration_readiness()
    _register_enterprise_litigation_dispute()
    _register_data_migration_readiness()
    _register_regulatory_readiness()
