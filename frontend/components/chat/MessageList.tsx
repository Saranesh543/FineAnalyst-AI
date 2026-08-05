"use client";

import { Turn } from "@/lib/types/chat";
import { AssistantAnswerText } from "./AssistantAnswerText";
import { EvidenceArtifactRenderer } from "../evidence/EvidenceArtifactRenderer";
import { User, Sparkles, CheckCircle2, CircleDashed, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface MessageListProps {
  messages: Turn[];
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
                  {msg.thinkingSteps.map((step) => (
                    <div key={step.id} className="flex items-center space-x-2 text-xs">
                      {step.status === "done" && <CheckCircle2 className="h-3 w-3 text-green-500" />}
                      {step.status === "running" && <CircleDashed className="h-3 w-3 text-blue-500 animate-spin" />}
                      {step.status === "error" && <XCircle className="h-3 w-3 text-red-500" />}
                      <span className={cn(
                        "font-medium", 
                        step.status === "done" ? "text-muted-foreground" : "text-foreground"
                      )}>
                        {step.label}
                      </span>
                    </div>
                  ))}
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
                        // This should ideally trigger a send, but we'd need to pass onSend down or use the store.
                        // For Phase 1, we can just leave it static or rely on store.
                        const el = document.querySelector('textarea');
                        if (el) {
                           el.value = suggestion;
                           // Trigger React onChange
                           const event = new Event('input', { bubbles: true });
                           el.dispatchEvent(event);
                           el.focus();
                        }
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
