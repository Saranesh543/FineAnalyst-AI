import { create } from 'zustand';
import { Turn, ThinkingStep, EvidenceArtifact } from '../types/chat';
import { agentClient } from '../api/agent-client';
import { v4 as uuidv4 } from 'uuid';

export interface FileAttachment {
  id: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  uploaded_at: string;
  status?: 'uploading' | 'done' | 'error';
  progress?: number;
}

export interface ConversationSession {
  id: string;
  title: string;
  isCustomTitle?: boolean;
  createdAt: string;
  updatedAt: string;
  messages: Turn[];
  attachments?: FileAttachment[];
}

interface ConversationState {
  currentAbortController: AbortController | null;
  activeSessionId: string | null;
  sessions: Record<string, ConversationSession>;
  stagedAttachments: FileAttachment[];
  isInitializing: boolean;
  
  sendMessage: (text: string) => Promise<void>;
  updateTurn: (id: string, updater: (turn: Turn) => Turn) => void;
  createNewSession: () => Promise<string>;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => Promise<void>;
  updateSessionTitle: (id: string, title: string, isCustom?: boolean) => Promise<void>;
  
  cancelRequest: () => void;
  init: (userId: string | null) => Promise<void>;
  
  uploadFile: (file: File) => Promise<void>;
  removeFile: (fileId: string) => Promise<void>;
  fetchSessionFiles: (sessionId: string) => Promise<void>;
}

export const useConversationStore = create<ConversationState>()((set, get) => ({
  currentAbortController: null,
  activeSessionId: null,
  sessions: {},
  stagedAttachments: [],
  isInitializing: true,

  cancelRequest: () => {
    const { currentAbortController } = get();
    if (currentAbortController) {
      currentAbortController.abort();
      set({ currentAbortController: null });
    }
  },

  init: async (userId: string | null) => {
    set({ isInitializing: true });
    
    if (!userId) {
      // Clear sessions on logout
      set({
        sessions: {},
        activeSessionId: null,
        stagedAttachments: [],
        isInitializing: false
      });
      return;
    }
    
    try {
      const backendSessions = await agentClient.fetchSessions();
      const sessionsMap: Record<string, ConversationSession> = {};
      
      let latestSessionId = null;
      let latestTime = 0;
      
      for (const bs of backendSessions) {
        // Hydrate each session
        const hydratedSession: ConversationSession = {
          id: bs.id,
          title: bs.title,
          isCustomTitle: bs.isCustomTitle,
          createdAt: bs.created_at,
          updatedAt: bs.updated_at,
          messages: bs.messages || []
        };
        sessionsMap[bs.id] = hydratedSession;
        
        const time = new Date(bs.updated_at).getTime();
        if (time > latestTime) {
          latestTime = time;
          latestSessionId = bs.id;
        }
      }
      
      set({
        sessions: sessionsMap,
        activeSessionId: latestSessionId,
        stagedAttachments: [],
        isInitializing: false
      });

      if (latestSessionId) {
        get().fetchSessionFiles(latestSessionId);
      }
      
    } catch (error) {
      console.error("[Store] Failed to initialize sessions from backend:", error);
      set({ isInitializing: false });
    }
  },

  fetchSessionFiles: async (sessionId: string) => {
    try {
      const files = await agentClient.getSessionFiles(sessionId);
      set((state) => {
        const session = state.sessions[sessionId];
        if (!session) return state;
        return {
          sessions: {
            ...state.sessions,
            [sessionId]: { ...session, attachments: files }
          }
        };
      });
    } catch (e) {
      console.error("[Store] Failed to fetch session files", e);
    }
  },

  uploadFile: async (file: File) => {
    let { activeSessionId, sessions } = get();
    if (!activeSessionId || !sessions[activeSessionId]) {
      activeSessionId = await get().createNewSession();
    }
    const tempId = uuidv4();
    const newAttachment: FileAttachment = {
      id: tempId,
      filename: file.name,
      file_type: file.name.split('.').pop() || 'unknown',
      size_bytes: file.size,
      uploaded_at: new Date().toISOString(),
      status: 'uploading',
      progress: 0
    };
    
    set((state) => ({
      stagedAttachments: [...state.stagedAttachments, newAttachment]
    }));

    try {
      const uploadedFile = await agentClient.uploadFile(activeSessionId!, file);
      set((state) => ({
        stagedAttachments: state.stagedAttachments.map(a => 
          a.id === tempId ? { ...uploadedFile, status: 'done' } : a
        )
      }));
    } catch (e) {
      console.error("[Store] Failed to upload file", e);
      set((state) => ({
        stagedAttachments: state.stagedAttachments.map(a => 
          a.id === tempId ? { ...a, status: 'error' } : a
        )
      }));
    }
  },

  removeFile: async (fileId: string) => {
    const { activeSessionId } = get();
    if (!activeSessionId) return;

    set((state) => ({
      stagedAttachments: state.stagedAttachments.filter(a => a.id !== fileId)
    }));

    try {
      await agentClient.deleteFile(fileId);
    } catch (e) {
      console.error("[Store] Failed to delete file", e);
    }
  },

  createNewSession: async () => {
    try {
      const bs = await agentClient.createSession();
      const newSession: ConversationSession = {
        id: bs.id,
        title: bs.title,
        isCustomTitle: false,
        createdAt: bs.created_at,
        updatedAt: bs.updated_at,
        messages: []
      };
      
      set((state) => ({
        activeSessionId: bs.id,
        sessions: {
          ...state.sessions,
          [bs.id]: newSession
        }
      }));
      return bs.id;
    } catch (error) {
      console.error("[Store] Failed to create backend session:", error);
      // Fallback optimistic UI
      const id = uuidv4();
      const now = new Date().toISOString();
      const newSession: ConversationSession = {
        id, title: "New Chat", createdAt: now, updatedAt: now, messages: []
      };
      set((state) => ({
        activeSessionId: id,
        sessions: { ...state.sessions, [id]: newSession }
      }));
      return id;
    }
  },

  switchSession: (id: string) => {
    set({ activeSessionId: id });
    get().fetchSessionFiles(id);
  },

  deleteSession: async (id: string) => {
    try {
      await agentClient.deleteSession(id);
    } catch (error) {
      console.error("[Store] Failed to delete backend session:", error);
    }
    
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
      return { sessions: newSessions, activeSessionId: newActiveId };
    });
  },

  updateSessionTitle: async (id: string, title: string, isCustom?: boolean) => {
    // Optimistic
    set((state) => {
      const session = state.sessions[id];
      if (!session) return state;
      return {
        sessions: {
          ...state.sessions,
          [id]: {
            ...session,
            title,
            isCustomTitle: isCustom !== undefined ? isCustom : session.isCustomTitle,
            updatedAt: new Date().toISOString()
          }
        }
      };
    });
    
    try {
      await agentClient.updateSessionTitle(id, title, isCustom);
    } catch (error) {
      console.error("[Store] Failed to update backend session title:", error);
    }
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
    const reqId = uuidv4().slice(0, 8);
    get().cancelRequest(); // Cancel any ongoing request

    let { activeSessionId, sessions, stagedAttachments, updateTurn, updateSessionTitle } = get();
    
    if (!activeSessionId || !sessions[activeSessionId]) {
      activeSessionId = await get().createNewSession();
    }

    const abortController = new AbortController();
    set({ 
      currentAbortController: abortController,
      stagedAttachments: [] // Clear staged attachments immediately
    });

    // 1. Add User Turn
    const userTurn: Turn = {
      id: uuidv4(),
      role: 'user',
      createdAt: new Date().toISOString(),
      userText: text,
      status: 'complete',
      attachments: stagedAttachments
    };
    
    // Save user turn to backend
    agentClient.saveTurn(activeSessionId, userTurn).catch(e => console.error("Failed to save user turn", e));
    
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

    // Faked animation setup
    let isFetching = true;
    const optimisticSteps: Omit<ThinkingStep, 'id'>[] = [];
    const baseLabels = [
       { kind: 'intent_routing', label: 'Understanding Question' },
       { kind: 'schema_discovery', label: 'Understanding Your Data' },
       { kind: 'sql_generation', label: 'Creating SQL Query' },
       { kind: 'sql_execution', label: 'Running Query' },
       { kind: 'visualization', label: 'Creating Chart' },
       { kind: 'insight_generation', label: 'Generating Insights' }
    ];

    (async () => {
       for (const step of baseLabels) {
          if (!isFetching) break;
          if (optimisticSteps.length > 0) optimisticSteps[optimisticSteps.length - 1].status = 'done';
          optimisticSteps.push({ ...step, status: 'running' } as any);
          get().updateTurn(assistantTurnId, t => ({
             ...t,
             thinkingSteps: optimisticSteps.map((s, idx) => ({ id: `opt-${idx}`, ...s })) as ThinkingStep[]
          }));
          await new Promise(r => setTimeout(r, 1200)); 
       }
    })();

    try {
      const currentSession = get().sessions[activeSessionId!];
      const previousTurns = currentSession.messages.filter(m => m.id !== userTurn.id && m.id !== assistantTurnId);
      const recentTurns = previousTurns.slice(-20);
      const history = recentTurns.map(m => {
        let content = m.role === 'user' ? (m.userText || "") : (m.answerText || "Analysis complete.");
        if (m.role === 'assistant' && m.evidence && m.evidence.length > 0) {
          const ev = m.evidence[0];
          if (ev.sql) content += `\n\n[Previous SQL Query Executed: ${ev.sql}]`;
        }
        return { role: m.role, content };
      });

      const analyzeRes = await agentClient.analyze({ 
        question: text, 
        session_id: activeSessionId,
        history, 
        signal: abortController.signal 
      });
      isFetching = false;
      const isDbIntent = analyzeRes.intent === 'database' || analyzeRes.intent === 'schema';

      let chatRes = null;
      if (!isDbIntent) {
        chatRes = await agentClient.chat({ message: text, session_id: activeSessionId, history, signal: abortController.signal });
      }

      get().updateTurn(assistantTurnId, t => ({
        ...t,
        thinkingSteps: analyzeRes.steps?.map((s: any) => ({
          id: uuidv4(),
          kind: s.name,
          label: s.name, 
          status: s.status,
          detail: s.detail,
          durationMs: s.duration_ms
        })) || []
      }));

      const evidence: EvidenceArtifact[] = [];
      if (analyzeRes.execution && analyzeRes.visualization) {
        const artifactChartType = analyzeRes.visualization.chart;
        const artifactTitle = analyzeRes.visualization.metadata?.title || 'Result Data';
        const artifactMetadata = analyzeRes.visualization.metadata;
        
        evidence.push({
          id: uuidv4(),
          kind: 'chart',
          chartType: artifactChartType as any,
          data: [],
          sql: analyzeRes.sql,
          rowCountTotal: analyzeRes.execution.row_count,
          rowSample: [],
          title: artifactTitle,
          insights: analyzeRes.insight,
          confidenceScore: analyzeRes.confidence_score,
          metadata: artifactMetadata
        });
      }

      if (evidence.length > 0 && Array.isArray(analyzeRes.execution.rows)) {
        const columns = analyzeRes.execution.columns || [];
        evidence[0].data = analyzeRes.execution.rows.map(row => {
          const obj: Record<string, any> = {};
          columns.forEach((col, i) => obj[col] = row[i]);
          return obj;
        });
        evidence[0].rowSample = evidence[0].data.slice(0, 5);
      }

      let answerText = chatRes?.message || '';
      if (isDbIntent && analyzeRes.insight) {
        const ins = analyzeRes.insight;
        answerText = `### Executive Summary\n${ins.summary}\n\n`;
        if (ins.key_findings?.length > 0) answerText += `### Key Insights\n${ins.key_findings.map((k: string) => `- ${k}`).join('\n')}\n\n`;
        if (ins.detailed_analysis) answerText += `### Detailed Analysis\n${ins.detailed_analysis}\n\n`;
        if (ins.recommendations?.length > 0) answerText += `### Recommendations\n${ins.recommendations.map((r: string, i: number) => `${i + 1}. ${r}`).join('\n')}\n\n`;
        if (ins.conclusion) answerText += `### Conclusion\n${ins.conclusion}`;
      } else if (isDbIntent) {
        answerText = 'Analysis complete.';
      }

      get().updateTurn(assistantTurnId, t => ({
        ...t,
        status: 'complete',
        answerText,
        evidence,
        followUpSuggestions: isDbIntent ? (analyzeRes.insight?.suggested_questions || analyzeRes.insight?.recommendations || []) : []
      }));

      // Generate title if new
      const currentSessionAfterComplete = get().sessions[activeSessionId!];
      if (previousTurns.length === 0 && !currentSessionAfterComplete.isCustomTitle) {
        let generatedTitle = "New Chat";
        const intent = analyzeRes.intent || 'conversation';
        if (intent === 'schema') generatedTitle = "Database Schema";
        else if (intent === 'database') {
          const stopWords = ['show', 'me', 'what', 'is', 'the', 'tell', 'about', 'how', 'many', 'much', 'do', 'we', 'have', 'are', 'there'];
          const words = text.split(' ').filter(w => !stopWords.includes(w.toLowerCase()));
          const keywords = words.slice(0, 3).join(' ');
          generatedTitle = keywords ? `${keywords.charAt(0).toUpperCase() + keywords.slice(1)} Analysis` : "Data Analysis";
        } else if (intent === 'knowledge') {
          const stopWords = ['explain', 'what', 'is', 'how', 'does', 'work', 'tell', 'me', 'about'];
          const words = text.split(' ').filter(w => !stopWords.includes(w.toLowerCase()));
          generatedTitle = words.slice(0, 3).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ') || "Knowledge Topic";
        } else {
          generatedTitle = text.split(' ').slice(0, 4).join(' ') + (text.split(' ').length > 4 ? '...' : '');
        }
        if (generatedTitle.length > 30) generatedTitle = generatedTitle.substring(0, 27) + '...';
        
        // Wait briefly for UI to settle before async call to avoid race conditions
        setTimeout(() => get().updateSessionTitle(activeSessionId!, generatedTitle), 100);
      }
      
      // Save assistant turn to backend
      const finalTurnState = get().sessions[activeSessionId!].messages.find(m => m.id === assistantTurnId);
      if (finalTurnState) {
        agentClient.saveTurn(activeSessionId!, finalTurnState).catch(e => console.error("Failed to save assistant turn", e));
      }

      set({ currentAbortController: null });

    } catch (error: any) {
      isFetching = false;
      
      if (error.name === 'AbortError') {
        console.log('[Store] Request was aborted');
        get().updateTurn(assistantTurnId, t => ({
          ...t,
          status: 'complete',
          answerText: t.answerText || "Request cancelled.",
        }));
        return;
      }
      
      let backendSteps: ThinkingStep[] = [];
      if (error.response?.data?.steps) {
        backendSteps = error.response.data.steps.map((s: any) => ({
          id: uuidv4(),
          kind: s.name,
          label: s.name,
          status: s.status,
          detail: s.detail,
          durationMs: s.duration_ms
        }));
      }

      get().updateTurn(assistantTurnId, t => ({
        ...t,
        status: 'error',
        answerText: "Sorry, I encountered an error while processing your request.",
        thinkingSteps: backendSteps.length > 0 ? backendSteps : t.thinkingSteps
      }));
      
      const errorTurnState = get().sessions[activeSessionId!].messages.find(m => m.id === assistantTurnId);
      if (errorTurnState) {
        agentClient.saveTurn(activeSessionId!, errorTurnState).catch(e => console.error("Failed to save error turn", e));
      }
    }
  }
}));
