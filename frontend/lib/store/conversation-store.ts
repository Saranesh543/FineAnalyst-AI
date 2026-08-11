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
  isGenerating: boolean;
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
  isGenerating: false,
  activeSessionId: null,
  sessions: {},
  stagedAttachments: [],
  isInitializing: true,

  cancelRequest: () => {
    const { currentAbortController } = get();
    if (currentAbortController) {
      currentAbortController.abort();
      set({ currentAbortController: null, isGenerating: false });
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
    let { activeSessionId, sessions, stagedAttachments, updateTurn, updateSessionTitle, isGenerating } = get();
    
    // Prevent parallel generations
    if (isGenerating) {
      console.log('[Store] A generation is already active. Stop it first.');
      return;
    }
    
    const reqId = uuidv4().slice(0, 8);
    
    if (!activeSessionId || !sessions[activeSessionId]) {
      activeSessionId = await get().createNewSession();
    }

    const abortController = new AbortController();
    set({ 
      currentAbortController: abortController,
      isGenerating: true,
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
      
      const cleanTurns = previousTurns.filter((turn, i, arr) => {
        if (turn.role === 'assistant') {
          return turn.status !== 'error';
        }
        if (turn.role === 'user') {
          const nextTurn = arr[i + 1];
          if (nextTurn && nextTurn.role === 'assistant' && nextTurn.status === 'error') {
            return false;
          }
        }
        return true;
      });

      const recentTurns = cleanTurns.slice(-6);
      const history = recentTurns.map(m => {
        let content = m.role === 'user' ? (m.userText || "") : (m.answerText || "Analysis complete.");
        if (m.role === 'assistant') {
          if (m.status === 'complete') {
            if (m.evidence && m.evidence.length > 0) {
            const ev = m.evidence[0];
            if (ev.sql) content += `\n\n[Previous SQL Query Executed: ${ev.sql}]`;
            }
          }
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
      if (analyzeRes.execution && (analyzeRes.visualizations || analyzeRes.visualization)) {
        const visualizations = analyzeRes.visualizations || [analyzeRes.visualization];
        
        console.log("[MERMAID RESPONSE] analyzeRes.visualizations:", visualizations);
        
        let commonData: any[] = [];
        let commonRowSample: any[] = [];
        
        if (Array.isArray(analyzeRes.execution.rows)) {
          const columns = analyzeRes.execution.columns || [];
          commonData = analyzeRes.execution.rows.map(row => {
            const obj: Record<string, any> = {};
            columns.forEach((col, i) => obj[col] = row[i]);
            return obj;
          });
          commonRowSample = commonData.slice(0, 5);
        }

        for (const vis of visualizations) {
          if (!vis) continue;
          
          const artifactChartType = vis.chart;
          const artifactTitle = vis.metadata?.title || 'Result Data';
          const artifactMetadata = vis.metadata;
          
          let validKeys: Set<string> | undefined;
          let chartData = commonData;
          
          // --- VALIDATION LAYER ---
          if (vis.x_axis || vis.y_axis) {
            const dataKeys = commonData.length > 0 ? Object.keys(commonData[0]) : [];
            const yKeys = vis.y_axis ? vis.y_axis.split(',').map((s: string) => s.trim()) : [];
            const xKey = vis.x_axis;
            
            let isValid = true;
            let invalidKey: string | null = null;
            
            if (xKey && !dataKeys.includes(xKey)) {
              isValid = false;
              invalidKey = xKey;
            }
            if (isValid) {
              for (const k of yKeys) {
                if (!dataKeys.includes(k)) {
                  isValid = false;
                  invalidKey = k;
                  break;
                }
              }
            }

            if (!isValid) {
               console.log(`[INVALID_KEY] Analysis ${assistantTurnId}: Key ${invalidKey} not found in data. Regenerating chart spec...`);
               console.log(`[DATASET SCHEMA] ${dataKeys.join(', ')}`);
               console.log(`[QUERY RESULT COLUMNS] ${dataKeys.join(', ')}`);
               console.log(`[CHART PLANNER INPUT] Old metadata: x=${xKey}, y=${vis.y_axis}`);
               
               // Regenerate chart specification based on actual schema
               const numericCols = dataKeys.filter(k => typeof commonData[0][k] === 'number' || (typeof commonData[0][k] === 'string' && !isNaN(parseFloat(commonData[0][k]))));
               const nonNumericCols = dataKeys.filter(k => !numericCols.includes(k));
               
               let newX = nonNumericCols.length > 0 ? nonNumericCols[0] : (numericCols.length > 0 ? numericCols[0] : null);
               let newY: string[] = [];
               for (const col of numericCols) {
                 if (col !== newX) newY.push(col);
               }
               // Fallback if no other numeric cols
               if (newY.length === 0 && numericCols.length > 0) newY.push(numericCols[0]);
               
               if (newY.length > 0 && newX) {
                 vis.x_axis = newX;
                 vis.y_axis = newY.join(',');
                 if (artifactMetadata) {
                   (artifactMetadata as any).x_axis = vis.x_axis;
                   (artifactMetadata as any).y_axis = vis.y_axis;
                   (artifactMetadata as any).chart_type = 'bar';
                 }
                 vis.chart = 'bar';
                 console.log(`[CHART PLANNER OUTPUT] New metadata: x=${vis.x_axis}, y=${vis.y_axis}, type=bar`);
               } else {
                 vis.x_axis = undefined;
                 vis.y_axis = undefined;
                 if (artifactMetadata) {
                   (artifactMetadata as any).x_axis = undefined;
                   (artifactMetadata as any).y_axis = undefined;
                   (artifactMetadata as any).chart_type = 'data_grid';
                 }
                 vis.chart = 'data_grid';
                 console.log(`[CHART PLANNER OUTPUT] New metadata: data_grid`);
               }
               console.log(`[CHART VALIDATION] Recovered for analysisId: ${assistantTurnId}`);
               console.log(`[EVIDENCE ARTIFACT PROPS] Rendering with new props.`);
            }

            // Apply validated or regenerated spec
            const newYKeys = vis.y_axis ? vis.y_axis.split(',').map((s: string) => s.trim()) : [];
            const newXKey = vis.x_axis;
            validKeys = new Set([...newYKeys]);
            if (newXKey) validKeys.add(newXKey);
            
            if (validKeys.size > 0 && vis.chart !== 'data_grid') {
               chartData = commonData.map(row => {
                 const filtered: Record<string, any> = {};
                 for (const k of validKeys!) {
                   if (k in row) filtered[k] = row[k];
                 }
                 return filtered;
               });
            }
          }
          // --- END VALIDATION LAYER ---

          let filteredInsights = analyzeRes.insight;
          if (analyzeRes.insight && validKeys && validKeys.size > 0 && vis.chart !== 'data_grid') {
            const validKeysArr = Array.from(validKeys);
            const filteredKpis = (analyzeRes.insight.kpi_cards || []).filter(kpi => {
              const labelLower = kpi.label.toLowerCase();
              return validKeysArr.some(k => {
                const normalizedKey = k.toLowerCase().replace(/_/g, ' ');
                return labelLower.includes(normalizedKey) || normalizedKey.includes(labelLower);
              });
            });
            filteredInsights = { ...analyzeRes.insight, kpi_cards: filteredKpis };
          }

          if (vis.chart === 'mermaid') {
            evidence.push({
              id: uuidv4(),
              analysisId: assistantTurnId,
              kind: 'mermaid',
              mermaidCode: artifactMetadata?.mermaid_code,
              mermaidError: artifactMetadata?.mermaid_error,
              diagramType: artifactMetadata?.diagram_type,
              data: chartData,
              sql: analyzeRes.sql || '',
              rowCountTotal: analyzeRes.execution?.row_count || 0,
              rowSample: commonRowSample,
              title: artifactTitle,
              insights: filteredInsights,
              confidenceScore: String(vis.confidence || analyzeRes.confidence_score || ''),
              metadata: artifactMetadata
            });
          } else {
            evidence.push({
              id: uuidv4(),
              analysisId: assistantTurnId,
              kind: 'chart',
              chartType: vis.chart as any,
              data: chartData,
              sql: analyzeRes.sql || '',
              rowCountTotal: analyzeRes.execution?.row_count || 0,
              rowSample: commonRowSample,
              title: artifactTitle,
              insights: filteredInsights,
              confidenceScore: String(vis.confidence || analyzeRes.confidence_score || ''),
              metadata: artifactMetadata
            });
          }
        }
        console.log("[MERMAID ARTIFACT] evidence artifacts:", evidence);
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
        queryPlan: analyzeRes.query_plan,
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
      
      set({ currentAbortController: null, isGenerating: false });

    } catch (error: any) {
      set({ currentAbortController: null, isGenerating: false });
      isFetching = false;
      
      if (error.name === 'AbortError') {
        console.log('[Store] Request was aborted');
        get().updateTurn(assistantTurnId, t => ({
          ...t,
          status: 'complete',
          answerText: t.answerText ? t.answerText : "*Generation stopped by user.*",
        }));
        
        // Save the cancelled turn to the backend to maintain consistency
        const finalTurnState = get().sessions[activeSessionId!].messages.find(m => m.id === assistantTurnId);
        if (finalTurnState) {
          agentClient.saveTurn(activeSessionId!, finalTurnState).catch(e => console.error("Failed to save cancelled turn", e));
        }
        
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

      let errorMessage = "Sorry, I encountered an error while processing your request.";
      if (error instanceof Error && error.message && !error.message.includes("HTTP 500")) {
        errorMessage = error.message;
      }

      get().updateTurn(assistantTurnId, t => ({
        ...t,
        status: 'error',
        answerText: errorMessage,
        thinkingSteps: backendSteps.length > 0 ? backendSteps : t.thinkingSteps
      }));
      
      const errorTurnState = get().sessions[activeSessionId!].messages.find(m => m.id === assistantTurnId);
      if (errorTurnState) {
        agentClient.saveTurn(activeSessionId!, errorTurnState).catch(e => console.error("Failed to save error turn", e));
      }
    }
  }
}));
