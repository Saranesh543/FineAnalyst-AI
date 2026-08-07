"use client";

import { Moon, Sun, Bell, MessageSquare, ChevronDown, User, LogOut, Settings } from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store/auth-store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function TopNav() {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-border/10 bg-background/50 backdrop-blur-md sticky top-0 z-50">
      <div className="flex items-center gap-8">
        <div className="text-xl font-medium tracking-tight flex items-center gap-1">
          <span>FineAnalyst</span>
        </div>
        <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
          {/* <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors cursor-not-allowed opacity-50" onClick={(e) => e.preventDefault()}>Dashboard</Link>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem disabled>Coming Soon</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu> */}

          <Link href="/" className="text-cyan-400 bg-cyan-400/10 px-3 py-1.5 rounded-full transition-colors border border-cyan-400/20">AI Chat</Link>

          {/* <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors cursor-not-allowed opacity-50" onClick={(e) => e.preventDefault()}>Data Explorer</Link>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem disabled>Coming Soon</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Link href="#" className="text-muted-foreground hover:text-foreground transition-colors cursor-not-allowed opacity-50" onClick={(e) => e.preventDefault()}>Help</Link>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem disabled>Coming Soon</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu> */}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="p-2 hover:bg-accent rounded-full transition-colors"
          >
            <Sun className="h-4 w-4 dark:hidden" />
            <Moon className="h-4 w-4 hidden dark:block" />
          </button>

          {/* <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="p-2 hover:bg-accent rounded-full transition-colors opacity-50 cursor-not-allowed">
                <MessageSquare className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem disabled>Messages (Coming Soon)</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu> */}

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="p-2 hover:bg-accent rounded-full transition-colors relative">
                <Bell className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem disabled className="text-muted-foreground">
                No notifications
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <div className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity ml-2">
              <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-500 flex items-center justify-center text-white text-xs font-bold overflow-hidden">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : "G"}
              </div>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem disabled className="opacity-100 font-medium cursor-default pointer-events-none text-foreground/90 py-3">
                <User className="mr-2 h-4 w-4" /> {user?.full_name || "Guest"}
              </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive cursor-pointer" onClick={handleLogout}>
              <LogOut className="mr-2 h-4 w-4" /> Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
