// RESOLUTION: 3. Standalone schema/ER endpoint: Yes, GET /schema exists. 4. Session state: Persisted server-side via AgentService. 6. Existing report/export tool: No existing tool in the backend agent.
const _rawUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const _cleanBase = _rawUrl.replace(/\/+$/, '');
const API_BASE = _cleanBase.endsWith('/api/v1') ? _cleanBase : `${_cleanBase}/api/v1`;

export interface AgentChatRequest {
  message: string;
  session_id?: string | null;
}

export interface AgentChatResponse {
  status: string;
  session_id: string | null;
  message: string;
}

export interface AnalyzeRequest {
  question: string;
  history?: string[];
}

export interface KPICard {
  label: string;
  value: string | number;
  format: string;
}

export interface AnalyzeResponse {
  question: string;
  intent?: string;
  sql: string;
  execution: {
    columns: string[];
    rows: any[][];
    row_count: number;
    execution_time_ms: number;
  };
  visualization: {
    chart: string;
    confidence?: number;
    reason?: string;
    metadata: {
      chart_type: string;
      title: string;
      encoding: Record<string, any>;
      description?: string;
    };
  };
  insight: {
    summary: string;
    kpi_cards: KPICard[];
    key_findings: string[];
    anomalies: string[];
    recommendations: string[];
    suggested_questions?: string[];
  };
  chart_metadata?: Record<string, any>;
  visualization_confidence?: number;
  confidence_score?: string;
}

export interface SchemaResponse {
  tables: any[];
}

export const agentClient = {
  async chat(payload: AgentChatRequest): Promise<AgentChatResponse> {
    console.log(`[AgentClient] chat fetch started... Payload:`, payload);
    const start = Date.now();
    try {
      const res = await fetch(`${API_BASE}/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      console.log(`[AgentClient] chat HTTP status: ${res.status}, Time: ${Date.now() - start}ms`);
      if (!res.ok) {
        throw new Error(`Failed to chat with agent (HTTP ${res.status})`);
      }
      const data = await res.json();
      console.log(`[AgentClient] chat response parsed successfully.`);
      return data;
    } catch (e) {
      console.error(`[AgentClient] chat fetch threw exception:`, e);
      throw e;
    }
  },

  async analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
    console.log(`[AgentClient] analyze fetch started... Payload:`, payload);
    const start = Date.now();
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      console.log(`[AgentClient] analyze HTTP status: ${res.status}, Time: ${Date.now() - start}ms`);
      if (!res.ok) {
        let errorMsg = `Failed to analyze (HTTP ${res.status})`;
        try {
          const errorData = await res.json();
          if (errorData.message) {
            errorMsg = errorData.message;
          } else if (errorData.detail) {
            errorMsg = JSON.stringify(errorData.detail);
          }
        } catch (e) {
          // Fallback if not JSON
        }
        throw new Error(errorMsg);
      }
      const data = await res.json();
      console.log(`[AgentClient] analyze response parsed successfully.`);
      return data;
    } catch (e) {
      console.error(`[AgentClient] analyze fetch threw exception:`, e);
      throw e;
    }
  },

  async getSchema(): Promise<SchemaResponse> {
    const res = await fetch(`${API_BASE}/schema`);
    if (!res.ok) {
      throw new Error("Failed to fetch schema");
    }
    return res.json();
  }
};
