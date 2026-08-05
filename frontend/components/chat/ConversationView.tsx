"use client";

import { useRef, useEffect } from "react";
import { useConversationStore } from "@/lib/store/conversation-store";
import { EmptyState } from "./EmptyState";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";

const EMPTY_ARRAY: any[] = [];

export function ConversationView() {
  const { sendMessage } = useConversationStore();
  const activeSessionId = useConversationStore(s => s.activeSessionId);
  const messages = useConversationStore(s => (activeSessionId && s.sessions[activeSessionId]) ? s.sessions[activeSessionId].messages : EMPTY_ARRAY);
  const isStreaming = messages.length > 0 && messages[messages.length - 1].status === "streaming";
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full w-full bg-background relative overflow-hidden">
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto scroll-smooth"
      >
        {messages.length === 0 ? (
          <EmptyState onSelectPrompt={(prompt) => sendMessage(prompt)} isStreaming={isStreaming} />
        ) : (
          <div className="pb-8">
            <MessageList messages={messages} />
          </div>
        )}
      </div>
      
      {messages.length > 0 && (
        <div className="w-full shrink-0 relative z-10 animate-in slide-in-from-bottom-4 duration-500">
          <Composer onSend={sendMessage} isStreaming={isStreaming} />
        </div>
      )}
    </div>
  );
}
