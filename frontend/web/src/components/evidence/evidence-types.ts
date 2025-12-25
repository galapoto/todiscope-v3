// Evidence entity types
export type EvidenceType = "document" | "structured_record";

export type EvidenceStatus = "verified" | "pending" | "disputed";

export interface BaseEvidence {
  id: string;
  type: EvidenceType;
  status: EvidenceStatus;
  source_engine: string;
  timestamp: string;
  hash?: string;
  checksum?: string;
  workflow_state?: string;
  linked_to?: string[]; // IDs of findings/metrics/insights
}

export interface DocumentEvidence extends BaseEvidence {
  type: "document";
  file_name: string;
  file_type: string;
  file_size?: number;
  file_url?: string;
  ocr_text?: string;
  ocr_confidence?: number;
  ocr_low_confidence_sections?: Array<{
    start: number;
    end: number;
    confidence: number;
  }>;
}

export interface StructuredRecordEvidence extends BaseEvidence {
  type: "structured_record";
  record_type: string; // "transaction" | "row" | "claim" | "log"
  data: Record<string, unknown>;
  source_table?: string;
  source_row_id?: string;
}

export type Evidence = DocumentEvidence | StructuredRecordEvidence;



