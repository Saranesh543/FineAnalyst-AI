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
        className="h-full overflow-y-auto scroll-smooth pb-[160px] md:pb-[140px]"
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
        <div className="absolute bottom-0 left-0 right-0 p-4 pb-6 md:p-6 md:pb-8 bg-gradient-to-t from-background via-background/95 to-transparent z-10 pointer-events-none animate-in slide-in-from-bottom-4 duration-500">
          <div className="max-w-[1000px] mx-auto w-full relative pointer-events-auto">
            <Composer onSend={sendMessage} isStreaming={isStreaming} />
          </div>
        </div>
      )}
    </div>
  );
}
