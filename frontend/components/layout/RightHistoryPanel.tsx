"use client";

import { MessageSquare, MoreVertical, Plus, Trash, Edit, Pin } from "lucide-react";
import { useConversationStore } from "@/lib/store/conversation-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { format, isToday, isYesterday, isThisWeek } from "date-fns";

export function RightHistoryPanel() {
  const { sessions, activeSessionId, createNewSession, switchSession, deleteSession } = useConversationStore();

  const sessionList = Object.values(sessions).sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  );

  const today = sessionList.filter(s => isToday(new Date(s.updatedAt)));
  const yesterday = sessionList.filter(s => isYesterday(new Date(s.updatedAt)));
  const last7Days = sessionList.filter(s => isThisWeek(new Date(s.updatedAt)) && !isToday(new Date(s.updatedAt)) && !isYesterday(new Date(s.updatedAt)));
  const older = sessionList.filter(s => !isToday(new Date(s.updatedAt)) && !isYesterday(new Date(s.updatedAt)) && !isThisWeek(new Date(s.updatedAt)));

  const renderSessionGroup = (title: string, items: typeof sessionList) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        <div className="space-y-1">
          {items.map((item) => (
            <div 
              key={item.id} 
              onClick={() => switchSession(item.id)}
              className={`flex flex-col gap-1 p-2 rounded-lg cursor-pointer group transition-all duration-200 ${
                activeSessionId === item.id ? "bg-cyan-500/10 border-transparent shadow-[inset_0_1px_0_0_rgba(34,211,238,0.1)]" : "hover:bg-white/5 border border-transparent"
              }`}
            >
              <div className="flex items-center justify-between text-sm">
                <div className={`flex items-center gap-2 truncate ${
                  activeSessionId === item.id ? "text-cyan-400 font-medium" : "text-foreground/90"
                }`}>
                  <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
                  <span className="truncate">{item.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {format(new Date(item.updatedAt), "HH:mm")}
                  </span>
                  
                  <div onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <button className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-background rounded">
                          <MoreVertical className="h-3 w-3" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {/* <DropdownMenuItem disabled className="text-muted-foreground cursor-not-allowed">
                          <Edit className="h-4 w-4 mr-2" /> Rename (Coming Soon)
                        </DropdownMenuItem>
                        <DropdownMenuItem disabled className="text-muted-foreground cursor-not-allowed">
                          <Pin className="h-4 w-4 mr-2" /> Pin (Coming Soon)
                        </DropdownMenuItem> */}
                        <DropdownMenuItem 
                          className="text-destructive focus:bg-destructive/10 cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(item.id);
                          }}
                        >
                          <Trash className="h-4 w-4 mr-2" /> Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="w-[300px] shrink-0 border-l border-border/10 bg-background/50 backdrop-blur-md hidden xl:flex flex-col h-full overflow-hidden">
      <div className="p-4 flex items-center justify-between">
        <h2 className="font-semibold text-lg">History Chat</h2>
        <button 
          onClick={createNewSession}
          className="flex items-center gap-1 text-sm font-medium text-cyan-400 hover:text-cyan-300 transition-all duration-200 hover:scale-105 active:scale-95 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 hover:shadow-[0_0_15px_rgba(34,211,238,0.2)]"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        {sessionList.length === 0 && (
          <div className="text-sm text-muted-foreground text-center mt-10">
            No history found.
          </div>
        )}
        {renderSessionGroup("Today", today)}
        {renderSessionGroup("Yesterday", yesterday)}
        {renderSessionGroup("Last 7 Days", last7Days)}
        {renderSessionGroup("Older", older)}
      </div>
      
      {/* Made by FineWorks Credit */}
      <div className="p-4 border-t border-border/10 text-xs text-muted-foreground/50 text-center">
        Made by <span className="text-cyan-500/70 font-medium">FineWorks</span>
      </div>
    </div>
  );
}
