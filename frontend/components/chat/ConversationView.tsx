"use client";

import { useRef, useEffect } from "react";
import { useConversationStore } from "@/lib/store/conversation-store";
import { EmptyState } from "./EmptyState";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";

export function ConversationView() {
  const { messages, sendMessage } = useConversationStore();
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
          <EmptyState onSelectPrompt={(prompt) => sendMessage(prompt)} />
        ) : (
          <div className="pb-8">
            <MessageList messages={messages} />
          </div>
        )}
      </div>
      
      <div className="w-full shrink-0 relative z-10">
        <Composer onSend={sendMessage} isStreaming={isStreaming} />
      </div>
    </div>
  );
}
