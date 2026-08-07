"use client";

import { Turn } from "@/lib/types/chat";
import { AssistantAnswerText } from "./AssistantAnswerText";
import { EvidenceArtifactRenderer } from "../evidence/EvidenceArtifactRenderer";
import { User, Sparkles, CheckCircle2, CircleDashed, XCircle, FastForward, ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useConversationStore } from "@/lib/store/conversation-store";

interface MessageListProps {
  messages: Turn[];
}

const STEP_LABELS: Record<string, string> = {
  "intent_routing": "Understanding Question",
  "schema_discovery": "Understanding Your Data",
  "sql_generation": "Creating SQL Query",
  "sql_execution": "Running Query",
  "visualization": "Creating Chart",
  "insight_generation": "Generating Insights"
};

function CollapsibleSQLCard({ sql }: { sql: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-2 w-full rounded-md border border-muted bg-muted/20 overflow-hidden">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 w-full px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/50 transition-colors"
      >
        {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span>View SQL</span>
      </button>
      
      {isOpen && (
        <div className="border-t border-muted bg-black/90 p-3 relative group">
          <button 
            onClick={handleCopy}
            className="absolute top-2 right-2 p-1.5 rounded-md bg-white/10 text-white hover:bg-white/20 transition-colors opacity-0 group-hover:opacity-100"
            title="Copy SQL"
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          </button>
          <pre className="text-[11px] text-cyan-400 font-mono overflow-x-auto whitespace-pre-wrap">
            <code>{sql}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) return null;

  return (
    <div className="flex flex-col space-y-8 py-8 w-full max-w-4xl mx-auto px-4">
      {messages.map((msg) => (
        <div key={msg.id} className={cn("flex flex-col w-full", msg.role === "user" ? "items-end" : "items-start")}>
          {msg.role === "user" ? (
            <div className="flex flex-col max-w-[85%] bg-primary text-primary-foreground px-5 py-3.5 rounded-2xl rounded-tr-sm shadow-sm">
              <span className="whitespace-pre-wrap">{msg.userText}</span>
            </div>
          ) : (
            <div className="flex flex-col w-full space-y-4">
              <div className="flex items-center space-x-2 text-primary font-medium">
                <div className="bg-primary/10 p-1.5 rounded-full">
                  <Sparkles className="h-4 w-4" />
                </div>
                <span>FineAnalyst</span>
              </div>
              
              {/* Thinking Steps */}
              {msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                <div className="flex flex-col space-y-1 mt-2 mb-4 bg-muted/30 border rounded-xl p-3 max-w-lg">
                  {msg.thinkingSteps.map((step) => {
                    const friendlyLabel = STEP_LABELS[step.kind] || step.label;
                    return (
                      <div key={step.id} className="flex flex-col mb-2 last:mb-0">
                        <div className="flex items-center space-x-2 text-xs w-full">
                          {step.status === "done" && <CheckCircle2 className="h-3 w-3 text-green-500" />}
                          {step.status === "running" && <CircleDashed className="h-3 w-3 text-blue-500 animate-spin" />}
                          {step.status === "error" && <XCircle className="h-3 w-3 text-red-500" />}
                          {step.status === "skipped" && <FastForward className="h-3 w-3 text-muted-foreground" />}
                          
                          <span className={cn(
                            "font-medium", 
                            step.status === "done" ? "text-muted-foreground" : "text-foreground",
                            step.status === "skipped" && "text-muted-foreground italic",
                            step.status === "error" && "text-red-500"
                          )}>
                            {friendlyLabel} {step.status === "skipped" && "(Skipped)"}
                          </span>

                          {step.durationMs !== undefined && (
                            <span className="ml-auto text-[10px] text-muted-foreground/60 font-mono">
                              {Math.round(step.durationMs)}ms
                            </span>
                          )}
                        </div>
                        
                        {/* Error details */}
                        {step.status === "error" && step.detail && (
                          <div className="mt-1 ml-5 text-xs text-red-400 bg-red-500/10 p-2 rounded border border-red-500/20">
                            {step.detail}
                          </div>
                        )}

                        {/* Collapsible SQL */}
                        {step.status === "done" && step.kind === "sql_generation" && step.detail && (
                          <div className="ml-5">
                            <CollapsibleSQLCard sql={step.detail} />
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Prose first */}
              <div className="pl-1">
                <AssistantAnswerText text={msg.answerText} isStreaming={msg.status === "streaming"} />
              </div>

              {/* Evidence second */}
              {msg.evidence && msg.evidence.length > 0 && (
                <div className="w-full">
                  <EvidenceArtifactRenderer evidence={msg.evidence} />
                </div>
              )}
              
              {/* Follow up suggestions */}
              {msg.followUpSuggestions && msg.followUpSuggestions.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t">
                  <span className="text-sm font-medium text-muted-foreground w-full mb-1">Suggested Next Questions:</span>
                  {msg.followUpSuggestions.map((suggestion, idx) => (
                    <button 
                      key={idx}
                      className="text-xs bg-accent hover:bg-accent/80 text-accent-foreground px-3 py-1.5 rounded-full border transition-colors"
                      onClick={() => {
                        const { sendMessage } = useConversationStore.getState();
                        sendMessage(suggestion);
                      }}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
