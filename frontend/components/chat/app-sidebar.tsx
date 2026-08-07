"use client";

import {
  MessageSquareIcon,
  BarChart2,
  Database,
  LayoutDashboard,
  FileText,
  Code,
  Settings,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback } from "react";
import { toast } from "sonner";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { useConversationStore } from "@/lib/store/conversation-store";

export function AppSidebar() {
  const router = useRouter();
  const { setOpenMobile, toggleSidebar, state } = useSidebar();
  const isCollapsed = state === "collapsed";
  const { createNewSession } = useConversationStore();

  const closeMobile = useCallback(() => {
    setOpenMobile(false);
  }, [setOpenMobile]);

  const handleToggleSidebar = useCallback(() => {
    toggleSidebar();
  }, [toggleSidebar]);

  const handleNewChat = useCallback(async (e: React.MouseEvent) => {
    e.preventDefault();
    await createNewSession();
    closeMobile();
    router.push("/");
  }, [createNewSession, closeMobile, router]);

  const navItems: Array<{
    title: string;
    icon: any;
    active?: boolean;
    disabled?: boolean;
    onClick?: (e: React.MouseEvent) => void;
  }> = [
    { title: "New Chat", icon: MessageSquareIcon, active: true, onClick: handleNewChat },
    // Temporarily hidden items - kept here for future features
    // { title: "Analytics (Coming Soon)", icon: BarChart2, active: false, disabled: true },
    // { title: "Data Sources (Coming Soon)", icon: Database, active: false, disabled: true },
    // { title: "Dashboards (Coming Soon)", icon: LayoutDashboard, active: false, disabled: true },
    // { title: "Reports (Coming Soon)", icon: FileText, active: false, disabled: true },
    // { title: "Saved Queries (Coming Soon)", icon: Code, active: false, disabled: true },
    // { title: "Settings (Coming Soon)", icon: Settings, active: false, disabled: true },
  ];

  return (
    <Sidebar collapsible="icon" variant="floating" className="border-none mt-4 mb-4 ml-4 h-[calc(100vh-2rem)] rounded-xl overflow-hidden shadow-float">
      <SidebarHeader className="pb-4 pt-6">
        <SidebarMenu>
          <SidebarMenuItem className="flex flex-row items-center justify-center">
            <div className="flex items-center justify-center w-full">
               {isCollapsed ? (
                 <BarChart2 className="size-6 text-cyan-400" />
               ) : (
                 <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-cyan-500/10 text-cyan-400 mb-2">
                   <BarChart2 className="size-6" />
                 </div>
               )}
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu className="gap-2 px-2">
              {navItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild={!item.disabled}
                    tooltip={item.title}
                    disabled={item.disabled}
                    onClick={item.onClick}
                    className={`h-11 rounded-lg transition-all duration-200 group ${
                      item.active
                        ? "bg-cyan-500/10 text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.1)]"
                        : "text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground"
                    } ${item.disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
                  >
                    {item.disabled ? (
                      <div className="flex flex-col items-center justify-center py-2 h-auto gap-1">
                        <item.icon className="size-5" />
                        {!isCollapsed && <span className="text-[10px] font-medium leading-none">{item.title}</span>}
                      </div>
                    ) : (
                      <a href="#" className="flex flex-col items-center justify-center py-2 h-auto gap-1">
                        <item.icon className={`size-5 ${item.active ? 'text-cyan-400' : ''}`} />
                        {!isCollapsed && <span className="text-[10px] font-medium leading-none">{item.title}</span>}
                      </a>
                    )}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="pb-4">
        <SidebarMenu>
          <SidebarMenuItem>
             <SidebarMenuButton
                onClick={handleToggleSidebar}
                className="h-10 rounded-lg text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground justify-center flex items-center"
              >
                {isCollapsed ? <ChevronRight className="size-5" /> : <ChevronLeft className="size-5" />}
              </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
