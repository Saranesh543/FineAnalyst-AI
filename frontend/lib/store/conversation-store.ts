// RESOLUTION: 5. Context/Memory: Purely implicit in backend prompt history. 7. Flowchart data: Insight generation emits only metric-answer-shaped data.
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Turn, ThinkingStep, EvidenceArtifact } from '../types/chat';
import { agentClient } from '../api/agent-client';
import { v4 as uuidv4 } from 'uuid';

export interface ConversationSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Turn[];
}

interface ConversationState {
  activeSessionId: string | null;
  sessions: Record<string, ConversationSession>;
  
  sendMessage: (text: string) => Promise<void>;
  updateTurn: (id: string, updater: (turn: Turn) => Turn) => void;
  createNewSession: () => string;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  updateSessionTitle: (id: string, title: string) => void;
  
  // Per-user isolation
  activeUserId: string | null;
  userSessions: Record<string, {
    activeSessionId: string | null;
    sessions: Record<string, ConversationSession>;
  }>;
  syncUser: (userId: string | null) => void;
}

export const useConversationStore = create<ConversationState>()(
  persist(
    (set, get) => ({
      activeSessionId: null,
      sessions: {},
      activeUserId: null,
      userSessions: {},

      syncUser: (userId: string | null) => set((state) => {
        if (state.activeUserId === userId) return state;
        
        const nextUserSessions = { ...state.userSessions };
        
        // Save current view to the departing user's bucket
        if (state.activeUserId) {
          nextUserSessions[state.activeUserId] = {
            activeSessionId: state.activeSessionId,
            sessions: state.sessions
          };
        }
        
        // Load the arriving user's bucket or empty state
        let nextActiveSessionId = null;
        let nextSessions = {};
        
        if (userId && nextUserSessions[userId]) {
          nextActiveSessionId = nextUserSessions[userId].activeSessionId;
          nextSessions = nextUserSessions[userId].sessions;
        }
        
        return {
          activeUserId: userId,
          activeSessionId: nextActiveSessionId,
          sessions: nextSessions,
          userSessions: nextUserSessions
        };
      }),

      createNewSession: () => {
        const id = uuidv4();
        const now = new Date().toISOString();
        const newSession: ConversationSession = {
          id,
          title: "New Chat",
          createdAt: now,
          updatedAt: now,
          messages: []
        };
        set((state) => ({
          activeSessionId: id,
          sessions: {
            ...state.sessions,
            [id]: newSession
          }
        }));
        return id;
      },

      switchSession: (id: string) => {
        set({ activeSessionId: id });
      },

      deleteSession: (id: string) => {
        set((state) => {
          const newSessions = { ...state.sessions };
          delete newSessions[id];
          
          let newActiveId = state.activeSessionId;
          if (state.activeSessionId === id) {
            const remainingIds = Object.keys(newSessions).sort((a, b) => 
              new Date(newSessions[b].updatedAt).getTime() - new Date(newSessions[a].updatedAt).getTime()
            );
            newActiveId = remainingIds.length > 0 ? remainingIds[0] : null;
          }

          if (!newActiveId) {
            // If no sessions remain, create an empty one per requirements
            const newId = uuidv4();
            const now = new Date().toISOString();
            newSessions[newId] = {
              id: newId,
              title: "New Chat",
              createdAt: now,
              updatedAt: now,
              messages: []
            };
            newActiveId = newId;
          }

          return {
            sessions: newSessions,
            activeSessionId: newActiveId
          };
        });
      },

      updateSessionTitle: (id: string, title: string) => {
        set((state) => {
          const session = state.sessions[id];
          if (!session) return state;
          return {
            sessions: {
              ...state.sessions,
              [id]: {
                ...session,
                title,
                updatedAt: new Date().toISOString()
              }
            }
          };
        });
      },

      updateTurn: (id, updater) => set((state) => {
        if (!state.activeSessionId) return state;
        const session = state.sessions[state.activeSessionId];
        if (!session) return state;

        return {
          sessions: {
            ...state.sessions,
            [state.activeSessionId]: {
              ...session,
              updatedAt: new Date().toISOString(),
              messages: session.messages.map(m => m.id === id ? updater(m) : m)
            }
          }
        };
      }),

      sendMessage: async (text: string) => {
        let { activeSessionId, sessions, updateTurn, updateSessionTitle } = get();
        
        if (!activeSessionId || !sessions[activeSessionId]) {
          activeSessionId = get().createNewSession();
        }

        const session = get().sessions[activeSessionId];
        
        // Auto-generate title on first message
        if (session.messages.length === 0) {
          updateSessionTitle(activeSessionId, text.slice(0, 40) + (text.length > 40 ? '...' : ''));
        }

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

        set((state) => {
          if (!state.activeSessionId) return state;
          const curSession = state.sessions[state.activeSessionId];
          return {
            sessions: {
              ...state.sessions,
              [state.activeSessionId]: {
                ...curSession,
                updatedAt: new Date().toISOString(),
                messages: [...curSession.messages, userTurn, assistantTurn]
              }
            }
          };
        });

        // Helper to add thinking step
        const appendThinking = (step: Omit<ThinkingStep, 'id'>) => {
          const id = uuidv4();
          get().updateTurn(assistantTurnId, t => ({
            ...t,
            thinkingSteps: [...(t.thinkingSteps || []), { id, ...step }]
          }));
        };

        try {
          appendThinking({ kind: 'schema_lookup', label: 'Analyzing schema', status: 'running' });

          // Pass clean question and history array separately
          // Only pass history from the current session
          const currentSession = get().sessions[activeSessionId!];
          const previousUserTurns = currentSession.messages.filter(m => m.role === 'user' && m.id !== userTurn.id);
          const history = previousUserTurns.map(m => m.userText || "");

          // Parallel calls (we pass activeSessionId as backend session_id if needed, though they are decoupled. We'll use activeSessionId)
          const chatPromise = agentClient.chat({ message: text, session_id: activeSessionId });
          const analyzePromise = agentClient.analyze({ question: text, history });

          const [chatRes, analyzeRes] = await Promise.all([chatPromise, analyzePromise]);

          const isDbIntent = analyzeRes.intent === 'database';

          // Synthesize thinking steps from analyze response
          get().updateTurn(assistantTurnId, t => ({
            ...t,
            thinkingSteps: isDbIntent
              ? t.thinkingSteps?.map(s => s.kind === 'schema_lookup' ? { ...s, status: 'done' } : s)
              : t.thinkingSteps?.filter(s => s.kind !== 'schema_lookup')
          }));

          if (analyzeRes.sql) {
            appendThinking({ kind: 'sql_generation', label: 'Wrote SQL query', status: 'done', detail: analyzeRes.sql });
          }
          if (analyzeRes.execution) {
            appendThinking({ kind: 'sql_execution', label: `Ran query (${analyzeRes.execution.row_count} rows)`, status: 'done' });
          }
          if (analyzeRes.visualization) {
            appendThinking({ kind: 'chart_recommendation', label: `Recommended ${analyzeRes.visualization.chart} chart`, status: 'done' });
          }
          if (analyzeRes.insight) {
            appendThinking({ kind: 'insight_generation', label: 'Generated insights', status: 'done' });
          }

          // Convert analyzeRes.execution + visualization to EvidenceArtifact
          const evidence: EvidenceArtifact[] = [];
          if (analyzeRes.execution && analyzeRes.visualization) {
            const artifactChartType = analyzeRes.visualization.chart;
            const artifactTitle = analyzeRes.visualization.metadata?.title || 'Result Data';
            const artifactMetadata = analyzeRes.visualization.metadata;
            
            evidence.push({
              id: uuidv4(),
              kind: 'chart',
              chartType: artifactChartType as any,
              data: [], // populated below
              sql: analyzeRes.sql,
              rowCountTotal: analyzeRes.execution.row_count,
              rowSample: [],
              title: artifactTitle,
              insights: analyzeRes.insight,
              confidenceScore: analyzeRes.confidence_score,
              metadata: artifactMetadata
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

          get().updateTurn(assistantTurnId, t => ({
            ...t,
            status: 'complete',
            answerText: isDbIntent ? (analyzeRes.insight?.summary || 'Analysis complete.') : chatRes.message,
            evidence,
            followUpSuggestions: isDbIntent ? (analyzeRes.insight?.suggested_questions || analyzeRes.insight?.recommendations || []) : []
          }));

        } catch (error: any) {
          get().updateTurn(assistantTurnId, t => ({
            ...t,
            status: 'error',
            answerText: `I encountered an error: ${error.message}`
          }));
        }
      }
    }),
    {
      name: 'fineanalyst_chat_history',
      partialize: (state) => ({
        activeSessionId: state.activeSessionId,
        sessions: Object.fromEntries(
          Object.entries(state.sessions).map(([id, session]) => [
            id,
            {
              ...session,
              messages: session.messages.map(m => {
                // Do not persist streaming or running steps. Convert them to error if they were left hanging
                if (m.status === 'streaming') {
                  return { ...m, status: 'error', answerText: 'Session interrupted before completion.' };
                }
                return m;
              })
            }
          ])
        )
      })
    }
  )
);
