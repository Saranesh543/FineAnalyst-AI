export interface ThinkingStep {
  id: string
  kind: "intent_routing" | "schema_lookup" | "schema_discovery" | "sql_generation" | "sql_execution" | "chart_recommendation" | "visualization" | "insight_generation" | string
  label: string
  status: "pending" | "running" | "done" | "error" | "skipped"
  detail?: string
  durationMs?: number
}

export interface EvidenceArtifact {
  id: string
  kind: "chart" | "table" | "single_metric" | "data_grid" | "map" | "kpi"
  chartType?: "bar" | "line" | "pie" | "scatter" | "data_grid" | "map" | "kpi"
  data: Record<string, any>[]
  encoding?: { x?: string; y?: string; series?: string }
  sql: string
  rowCountTotal: number
  rowSample: Record<string, any>[]
  title: string
  insights?: {
    summary: string;
    kpi_cards: { label: string; value: string | number; format: string }[];
    key_findings: string[];
    anomalies: string[];
    recommendations: string[];
    suggested_questions?: string[];
  }
  confidenceScore?: string;
  metadata?: Record<string, any>;
}

export interface Turn {
  id: string
  role: "user" | "assistant"
  createdAt: string
  userText?: string
  thinkingSteps?: ThinkingStep[]
  answerText?: string
  evidence?: EvidenceArtifact[]
  followUpSuggestions?: string[]
  status: "streaming" | "complete" | "error"
}
