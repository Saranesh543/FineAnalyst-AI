// RESOLUTION: 5. Context/Memory: Purely implicit in backend prompt history. 7. Flowchart data: Insight generation emits only metric-answer-shaped data.
import { create } from 'zustand';
import { Turn, ThinkingStep, EvidenceArtifact } from '../types/chat';
import { agentClient } from '../api/agent-client';
import { v4 as uuidv4 } from 'uuid';

interface ConversationState {
  sessionId: string | null;
  messages: Turn[];
  sendMessage: (text: string) => Promise<void>;
  updateTurn: (id: string, updater: (turn: Turn) => Turn) => void;
  clearSession: () => void;
}

export const useConversationStore = create<ConversationState>((set, get) => ({
  sessionId: null,
  messages: [],
  clearSession: () => set({ sessionId: null, messages: [] }),
  updateTurn: (id, updater) => set((state) => ({
    messages: state.messages.map(m => m.id === id ? updater(m) : m)
  })),
  sendMessage: async (text: string) => {
    const { sessionId, updateTurn } = get();
    
    // 1. Add User Turn
    const userTurn: Turn = {
      id: uuidv4(),
      role: 'user',
      createdAt: new Date().toISOString(),
      userText: text,
      status: 'complete'
    };
    
    // 2. Add Assistant Turn (streaming)
    const assistantTurnId = uuidv4();
    const assistantTurn: Turn = {
      id: assistantTurnId,
      role: 'assistant',
      createdAt: new Date().toISOString(),
      status: 'streaming',
      thinkingSteps: [],
      answerText: '',
      evidence: []
    };

    set((state) => ({ messages: [...state.messages, userTurn, assistantTurn] }));

    // Helper to add thinking step
    const appendThinking = (step: Omit<ThinkingStep, 'id'>) => {
      const id = uuidv4();
      updateTurn(assistantTurnId, t => ({
        ...t,
        thinkingSteps: [...(t.thinkingSteps || []), { id, ...step }]
      }));
    };

    try {
      appendThinking({ kind: 'schema_lookup', label: 'Analyzing schema', status: 'running' });

      // Build self-contained question using accumulated client-side history for /analyze
      let analyzeQuestion = text;
      const previousUserTurns = get().messages.filter(m => m.role === 'user' && m.id !== userTurn.id);
      if (previousUserTurns.length > 0) {
        const allQuestions = previousUserTurns.map(m => m.userText).join(' | ');
        analyzeQuestion = `Previous context from conversation history: [${allQuestions}]. New question: "${text}". Please answer the new question fully incorporating the previous context where relevant.`;
      }

      // Parallel calls
      const chatPromise = agentClient.chat({ message: text, session_id: sessionId });
      const analyzePromise = agentClient.analyze({ question: analyzeQuestion });

      const [chatRes, analyzeRes] = await Promise.all([chatPromise, analyzePromise]);

      if (chatRes.session_id && !sessionId) {
        set({ sessionId: chatRes.session_id });
      }

      // Synthesize thinking steps from analyze response
      // Replace running schema step with done
      updateTurn(assistantTurnId, t => ({
        ...t,
        thinkingSteps: t.thinkingSteps?.map(s => s.kind === 'schema_lookup' ? { ...s, status: 'done' } : s)
      }));

      if (analyzeRes.sql) {
        appendThinking({ kind: 'sql_generation', label: 'Wrote SQL query', status: 'done', detail: analyzeRes.sql });
      }
      if (analyzeRes.execution) {
        appendThinking({ kind: 'sql_execution', label: `Ran query (${analyzeRes.execution.row_count} rows)`, status: 'done' });
      }
      if (analyzeRes.visualization) {
        appendThinking({ kind: 'chart_recommendation', label: `Recommended ${analyzeRes.visualization.chart_type} chart`, status: 'done' });
      }
      if (analyzeRes.insight) {
        appendThinking({ kind: 'insight_generation', label: 'Generated insights', status: 'done' });
      }

      // Convert analyzeRes.execution + visualization to EvidenceArtifact
      const evidence: EvidenceArtifact[] = [];
      if (analyzeRes.execution && analyzeRes.visualization) {
        evidence.push({
          id: uuidv4(),
          kind: 'chart', // or table depending on logic, let's say chart if chart_type isn't 'table'
          chartType: analyzeRes.visualization.chart_type as any,
          data: [], // populated below
          sql: analyzeRes.sql,
          rowCountTotal: analyzeRes.execution.row_count,
          rowSample: [],
          title: analyzeRes.visualization.title || 'Result Data',
          insights: analyzeRes.insight,
          confidenceScore: analyzeRes.confidence_score
        });
      }

      // Actually map rows if they are arrays, to Record based on columns
      if (evidence.length > 0 && Array.isArray(analyzeRes.execution.rows)) {
        const columns = analyzeRes.execution.columns || [];
        evidence[0].data = analyzeRes.execution.rows.map(row => {
          const obj: Record<string, any> = {};
          columns.forEach((col, i) => {
            obj[col] = row[i];
          });
          return obj;
        });
        evidence[0].rowSample = evidence[0].data.slice(0, 5);
      }

      updateTurn(assistantTurnId, t => ({
        ...t,
        status: 'complete',
        answerText: analyzeRes.insight?.summary || 'Analysis complete.',
        evidence,
        followUpSuggestions: analyzeRes.insight?.suggested_questions || analyzeRes.insight?.recommendations || []
      }));

    } catch (error: any) {
      updateTurn(assistantTurnId, t => ({
        ...t,
        status: 'error',
        answerText: `I encountered an error: ${error.message}`
      }));
    }
  }
}));
