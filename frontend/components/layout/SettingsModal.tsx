"use client";

import { useState } from "react";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/lib/store/auth-store";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Moon, Sun, Monitor, User, LogOut, Info, Settings as SettingsIcon, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface SettingsModalProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
}

type Tab = "general" | "account" | "chat" | "about";

export function SettingsModal({ isOpen, onOpenChange }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>("general");
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    onOpenChange(false);
    logout();
    router.push("/login");
  };

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: "general", label: "General", icon: SettingsIcon },
    { id: "account", label: "Account", icon: User },
    { id: "chat", label: "Chat", icon: MessageSquare },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] w-full md:max-w-3xl h-[85vh] md:h-[600px] flex flex-col p-0 gap-0 overflow-hidden bg-background border-border/20 shadow-2xl rounded-2xl md:rounded-3xl">
        <DialogHeader className="px-4 py-4 md:px-6 md:py-5 border-b border-border/10 bg-card/30 backdrop-blur-md">
          <DialogTitle className="text-xl font-semibold flex items-center gap-2">
            <SettingsIcon className="w-5 h-5 text-cyan-400" />
            Settings
          </DialogTitle>
          <DialogDescription className="sr-only">
            Manage your FineAnalyst preferences and account settings.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
          {/* Sidebar Tabs */}
          <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-border/10 bg-card/10 flex md:flex-col overflow-x-auto md:overflow-y-auto hide-scrollbar p-2 md:p-4 gap-1 md:gap-2 shrink-0">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 md:px-4 md:py-3 rounded-lg md:rounded-xl text-sm font-medium transition-all duration-200 whitespace-nowrap outline-none",
                  activeTab === tab.id
                    ? "bg-cyan-500/10 text-cyan-400 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.2)]"
                    : "text-muted-foreground hover:bg-card/40 hover:text-foreground"
                )}
              >
                <tab.icon className={cn("w-4 h-4", activeTab === tab.id ? "text-cyan-400" : "opacity-70")} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar">
            <div className="max-w-2xl mx-auto space-y-8 pb-8">
              {/* GENERAL TAB */}
              {activeTab === "general" && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-lg font-medium mb-1 text-foreground">Appearance</h3>
                    <p className="text-sm text-muted-foreground mb-4">Customize how FineAnalyst looks on your device.</p>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <button
                        onClick={() => setTheme("light")}
                        className={cn(
                          "flex flex-col items-center justify-center p-4 rounded-xl border transition-all gap-3 bg-card/20",
                          theme === "light" ? "border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.15)] ring-1 ring-cyan-400/50" : "border-border/10 hover:border-border/30 hover:bg-card/40"
                        )}
                      >
                        <Sun className={cn("w-6 h-6", theme === "light" ? "text-cyan-400" : "text-muted-foreground")} />
                        <span className="text-sm font-medium">Light</span>
                      </button>
                      <button
                        onClick={() => setTheme("dark")}
                        className={cn(
                          "flex flex-col items-center justify-center p-4 rounded-xl border transition-all gap-3 bg-card/20",
                          theme === "dark" ? "border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.15)] ring-1 ring-cyan-400/50" : "border-border/10 hover:border-border/30 hover:bg-card/40"
                        )}
                      >
                        <Moon className={cn("w-6 h-6", theme === "dark" ? "text-cyan-400" : "text-muted-foreground")} />
                        <span className="text-sm font-medium">Dark</span>
                      </button>
                      <button
                        onClick={() => setTheme("system")}
                        className={cn(
                          "flex flex-col items-center justify-center p-4 rounded-xl border transition-all gap-3 bg-card/20",
                          theme === "system" ? "border-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.15)] ring-1 ring-cyan-400/50" : "border-border/10 hover:border-border/30 hover:bg-card/40"
                        )}
                      >
                        <Monitor className={cn("w-6 h-6", theme === "system" ? "text-cyan-400" : "text-muted-foreground")} />
                        <span className="text-sm font-medium">System</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* ACCOUNT TAB */}
              {activeTab === "account" && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-lg font-medium mb-1 text-foreground">Profile Information</h3>
                    <p className="text-sm text-muted-foreground mb-4">Your current active session details.</p>
                    
                    <div className="bg-card/20 border border-border/10 rounded-xl p-5 space-y-4">
                      <div className="flex items-center gap-4">
                        <div className="h-16 w-16 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-500 flex items-center justify-center text-white text-2xl font-bold overflow-hidden shadow-lg">
                          {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "G"}
                        </div>
                        <div>
                          <p className="font-semibold text-lg text-foreground">{user?.full_name || "Guest User"}</p>
                          <p className="text-sm text-muted-foreground">{user?.email || "Not signed in"}</p>
                        </div>
                      </div>
                      
                      <div className="pt-4 border-t border-border/10">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div>
                            <p className="text-sm font-medium text-foreground">Account Status</p>
                            <p className="text-xs text-muted-foreground">Persistent active session</p>
                          </div>
                          <Button 
                            variant="destructive" 
                            className="bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white border border-red-500/20 transition-all w-full sm:w-auto"
                            onClick={handleLogout}
                          >
                            <LogOut className="w-4 h-4 mr-2" />
                            Log Out
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* CHAT TAB */}
              {activeTab === "chat" && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <h3 className="text-lg font-medium mb-1 text-foreground">Conversation Preferences</h3>
                    <p className="text-sm text-muted-foreground mb-4">Manage how AI chats operate.</p>
                    
                    <div className="bg-card/20 border border-border/10 rounded-xl p-5 space-y-4">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2">
                        <div>
                          <p className="font-medium text-sm text-foreground">Memory</p>
                          <p className="text-xs text-muted-foreground">Context retained within each individual chat session.</p>
                        </div>
                        <span className="text-xs font-semibold px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">Enabled</span>
                      </div>
                      
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2 border-t border-border/10 pt-4">
                        <div>
                          <p className="font-medium text-sm text-foreground">Data Visualizations</p>
                          <p className="text-xs text-muted-foreground">AI automatically generates charts and diagrams.</p>
                        </div>
                        <span className="text-xs font-semibold px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">Enabled</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ABOUT TAB */}
              {activeTab === "about" && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex flex-col items-center text-center p-6 bg-card/10 border border-border/10 rounded-2xl">
                    <div className="h-16 w-16 bg-gradient-to-tr from-cyan-400 to-blue-500 rounded-2xl flex items-center justify-center mb-4 shadow-glow rotate-3">
                      <span className="text-2xl font-bold text-white -rotate-3">FA</span>
                    </div>
                    <h3 className="text-xl font-bold text-foreground">FineAnalyst AI</h3>
                    <p className="text-sm text-muted-foreground mt-1">Version 1.0.0</p>
                    <p className="text-sm text-foreground/80 mt-4 max-w-sm">
                      An AI-powered data analysis platform designed to help users understand datasets, generate analytical insights, and visualize data.
                    </p>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-semibold text-foreground mb-3 uppercase tracking-wider">Created By</h4>
                    <div className="bg-card/20 border border-border/10 rounded-xl p-5 space-y-2">
                      <p className="font-semibold text-cyan-400 text-lg">FineWorks</p>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        FineWorks is the technology team behind FineAnalyst. The team consists of Saranesh, Praveen Balaji, Nitish, and Sakthi Saran.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
