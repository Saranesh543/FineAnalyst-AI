// RESOLUTION: 3. Standalone schema/ER endpoint: Yes, GET /schema exists. 4. Session state: Persisted server-side via AgentService. 6. Existing report/export tool: No existing tool in the backend agent.
const API_BASE = "http://localhost:8000/api/v1";

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
}

export interface AnalyzeResponse {
  question: string;
  sql: string;
  execution: {
    columns: string[];
    rows: any[][];
    row_count: number;
    execution_time_ms: number;
  };
  visualization: {
    chart_type: string;
    encoding: any;
    title: string;
  };
  insight: {
    summary: string;
    key_findings: string[];
    anomalies: string[];
    recommendations: string[];
  };
}

export interface SchemaResponse {
  tables: any[];
}

export const agentClient = {
  async chat(payload: AgentChatRequest): Promise<AgentChatResponse> {
    const res = await fetch(`${API_BASE}/agent/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("Failed to chat with agent");
    }
    return res.json();
  },

  async analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      let errorMsg = "Failed to analyze";
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
    return res.json();
  },

  async getSchema(): Promise<SchemaResponse> {
    const res = await fetch(`${API_BASE}/schema`);
    if (!res.ok) {
      throw new Error("Failed to fetch schema");
    }
    return res.json();
  }
};
