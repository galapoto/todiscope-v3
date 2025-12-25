export type EngineCapability =
  | "dashboards"
  | "reports"
  | "evidence"
  | "workflows"
  | "ai";

export type ExportFormat = "pdf" | "csv" | "xlsx";

export type EngineSummary = {
  engine_id: string;
  enabled: boolean;
  display_name: string;
  description?: string;
  capabilities: ReadonlyArray<EngineCapability>;
  supported_export_formats: ReadonlyArray<ExportFormat>;
};

export type EngineMetric = {
  id: string;
  engine_id: string;
  dataset_version_id: string;
  name: string;
  value: number | string | boolean;
  unit?: string;
  updated_at: string;
};

export type EngineEvidenceRef = {
  id: string;
  kind?: string;
  title?: string;
  uri?: string;
};

export type EngineFinding = {
  id: string;
  engine_id: string;
  dataset_version_id: string;
  title: string;
  description?: string;
  severity?: "low" | "medium" | "high" | "critical";
  evidence?: EngineEvidenceRef[];
  workflow_status?: string;
  created_at?: string;
};

