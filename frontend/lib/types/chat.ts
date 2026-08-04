export interface ThinkingStep {
  id: string
  kind: "schema_lookup" | "sql_generation" | "sql_execution" | "chart_recommendation" | "insight_generation"
  label: string
  status: "pending" | "running" | "done" | "error"
  detail?: string
}

export interface EvidenceArtifact {
  id: string
  kind: "chart" | "table" | "single_metric"
  chartType?: "bar" | "line" | "pie" | "scatter"
  data: Record<string, any>[]
  encoding?: { x?: string; y?: string; series?: string }
  sql: string
  rowCountTotal: number
  rowSample: Record<string, any>[]
  title: string
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
