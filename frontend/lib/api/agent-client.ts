import { useAuthStore } from '../store/auth-store';

const _rawUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const _cleanBase = _rawUrl.replace(/\/+$/, '');
const API_BASE = _cleanBase.endsWith('/api/v1') ? _cleanBase : `${_cleanBase}/api/v1`;

export interface AgentChatRequest {
  message: string;
  session_id?: string | null;
  history?: { role: string; content: string }[];
}

export interface AgentChatResponse {
  status: string;
  session_id: string | null;
  message: string;
}

export interface AnalyzeRequest {
  question: string;
  history?: { role: string; content: string }[];
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

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  let token = useAuthStore.getState().token;
  
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    console.log(`[AgentClient] 401 received, attempting to refresh token...`);
    await useAuthStore.getState().verifyToken();
    token = useAuthStore.getState().token;
    
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
      res = await fetch(url, { ...options, headers });
    }
  }

  return res;
}

export const agentClient = {
  async chat(payload: AgentChatRequest): Promise<AgentChatResponse> {
    console.log(`[AgentClient] chat fetch started... Payload:`, payload);
    const start = Date.now();
    try {
      const res = await fetchWithAuth(`${API_BASE}/agent/chat`, {
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
      const res = await fetchWithAuth(`${API_BASE}/analyze`, {
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
    const res = await fetchWithAuth(`${API_BASE}/schema`);
    if (!res.ok) {
      throw new Error("Failed to fetch schema");
    }
    return res.json();
  },

  async fetchSessions(): Promise<any[]> {
    const res = await fetchWithAuth(`${API_BASE}/sessions`);
    if (!res.ok) throw new Error("Failed to fetch sessions");
    return res.json();
  },

  async createSession(): Promise<any> {
    const res = await fetchWithAuth(`${API_BASE}/sessions`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create session");
    return res.json();
  },

  async updateSessionTitle(id: string, title: string, isCustomTitle?: boolean): Promise<void> {
    const res = await fetchWithAuth(`${API_BASE}/sessions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, isCustomTitle }),
    });
    if (!res.ok) throw new Error("Failed to update session title");
  },

  async deleteSession(id: string): Promise<void> {
    const res = await fetchWithAuth(`${API_BASE}/sessions/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete session");
  },

  async saveTurn(sessionId: string, turn: any): Promise<void> {
    const res = await fetchWithAuth(`${API_BASE}/sessions/${sessionId}/turns`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(turn),
    });
    if (!res.ok) throw new Error("Failed to save turn");
  }
};
