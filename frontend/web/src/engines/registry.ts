import type { EngineCapability, EngineSummary, ExportFormat } from "./types";

export type EngineDefinition = Omit<EngineSummary, "enabled"> & {
  /**
   * Optional engine-specific status endpoint. If absent, status is treated as unsupported.
   * Example: `/api/v3/engines/cost-intelligence/status`.
   */
  status_endpoint?: string;
};

const formats = (...f: ExportFormat[]) => f;
const caps = (...c: EngineCapability[]) => c;

/**
 * Central frontend engine registry.
 *
 * This is intentionally frontend-owned so UI never needs to special-case engines.
 * The backend remains authoritative for *enabled* engines.
 */
export const engineRegistry: Record<string, EngineDefinition> = {
  "engine_csrd": {
    engine_id: "engine_csrd",
    display_name: "CSRD & ESRS Compliance",
    description:
      "Analyzes ESG and financial data to assess compliance with Corporate Sustainability Reporting Directive (CSRD) and European Sustainability Reporting Standards (ESRS). Calculates emissions, assesses double materiality, and generates compliance reports.",
    capabilities: caps("dashboards", "evidence", "reports"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_financial_forensics": {
    engine_id: "engine_financial_forensics",
    display_name: "Financial Forensics & Leakage",
    description:
      "Detects financial anomalies, leakage patterns, and potential fraud indicators in financial transaction data. Analyzes spending patterns, identifies outliers, and generates forensic reports.",
    capabilities: caps("dashboards", "reports", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_construction_cost_intelligence": {
    engine_id: "engine_construction_cost_intelligence",
    display_name: "Construction & Infrastructure Cost Intelligence",
    description:
      "Compares budgeted costs (BOQ) against actual costs for construction and infrastructure projects. Identifies cost variances, analyzes trends, and generates cost intelligence reports.",
    capabilities: caps("dashboards", "reports", "evidence"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
    status_endpoint: "/api/v3/engines/cost-intelligence/status",
  },
  "engine_audit_readiness": {
    engine_id: "engine_audit_readiness",
    display_name: "Audit Readiness & Data Cleanup",
    description:
      "Assesses data quality and readiness for audit processes. Identifies data inconsistencies, missing information, and compliance gaps. Prepares datasets for audit review. Note: This engine does not support report generation.",
    capabilities: caps("dashboards", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_enterprise_capital_debt_readiness": {
    engine_id: "engine_enterprise_capital_debt_readiness",
    display_name: "Capital & Loan Readiness",
    description:
      "Evaluates enterprise readiness for capital raising and loan applications. Analyzes financial health, debt capacity, and compliance with lending criteria. Generates readiness assessments and reports.",
    capabilities: caps("dashboards", "reports", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_data_migration_readiness": {
    engine_id: "engine_data_migration_readiness",
    display_name: "Data Migration & ERP Readiness",
    description:
      "Assesses data quality and readiness for ERP system migration. Identifies data mapping issues, validation errors, and migration risks. Prepares data for system transitions. Note: This engine does not support report generation.",
    capabilities: caps("dashboards", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_erp_integration_readiness": {
    engine_id: "engine_erp_integration_readiness",
    display_name: "ERP Integration Readiness",
    description:
      "Evaluates readiness for ERP system integration. Analyzes data formats, validates integration requirements, and identifies potential integration challenges. Note: This engine does not support report generation.",
    capabilities: caps("dashboards", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_enterprise_deal_transaction_readiness": {
    engine_id: "engine_enterprise_deal_transaction_readiness",
    display_name: "Deal & Transaction Readiness",
    description:
      "Assesses enterprise readiness for M&A transactions, divestitures, and other deal structures. Analyzes financial data, identifies deal risks, and generates transaction readiness reports.",
    capabilities: caps("dashboards", "reports", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_enterprise_litigation_dispute": {
    engine_id: "engine_enterprise_litigation_dispute",
    display_name: "Litigation & Dispute Analysis",
    description:
      "Analyzes legal disputes and litigation scenarios. Assesses damages, liability exposure, and legal consistency. Generates litigation analysis reports for legal proceedings.",
    capabilities: caps("dashboards", "reports", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_regulatory_readiness": {
    engine_id: "engine_regulatory_readiness",
    display_name: "Regulatory Readiness (Non-CSRD)",
    description:
      "Evaluates compliance with regulatory frameworks beyond CSRD. Assesses data quality, identifies compliance gaps, and prepares regulatory submissions. Note: This engine does not support report generation.",
    capabilities: caps("dashboards", "evidence"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_enterprise_insurance_claim_forensics": {
    engine_id: "engine_enterprise_insurance_claim_forensics",
    display_name: "Insurance Claim Forensics",
    description:
      "Analyzes insurance claims for fraud detection, validation, and forensic investigation. Identifies suspicious patterns, validates claim data, and generates forensic analysis. Note: This engine does not support report generation.",
    capabilities: caps("dashboards", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
  "engine_distressed_asset_debt_stress": {
    engine_id: "engine_distressed_asset_debt_stress",
    display_name: "Distressed Asset & Debt Analysis",
    description:
      "Analyzes distressed assets and debt stress scenarios. Evaluates recovery potential, assesses restructuring options, and generates stress test analysis. Note: This engine does not support report generation.",
    capabilities: caps("dashboards", "evidence", "workflows"),
    supported_export_formats: formats("pdf", "csv", "xlsx"),
  },
};

export function getEngineDefinition(engineId: string): EngineDefinition {
  return (
    engineRegistry[engineId] ??
    {
      engine_id: engineId,
      display_name: engineId,
      capabilities: [],
      supported_export_formats: [],
    }
  );
}
