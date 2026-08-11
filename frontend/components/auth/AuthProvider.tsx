"use client";

import { useAuthStore } from "@/lib/store/auth-store";
import { useRouter, usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, verifyToken } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // On mount: validate token and hydrate sessions from backend
    verifyToken().finally(() => {
      setMounted(true);
    });
  }, [verifyToken]);

  useEffect(() => {
    if (!mounted) return;
    const isAuthRoute = ["/login", "/register", "/forgot-password", "/reset-password"].includes(pathname);
    
    if (!isAuthenticated && !isAuthRoute) {
      router.push("/login");
    } else if (isAuthenticated && isAuthRoute) {
      router.push("/");
    }
  }, [isAuthenticated, pathname, router, mounted]);

  // Prevent flash of protected content while evaluating redirect
  if (!mounted) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background relative overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-500/10 blur-[120px] pointer-events-none" />
        <div className="flex flex-col items-center gap-4 animate-in fade-in duration-500">
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-1">
            <span>FineAnalyst</span>
          </h1>
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
        </div>
      </div>
    );
  }
  
  const isAuthRoute = ["/login", "/register", "/forgot-password", "/reset-password"].includes(pathname);
  if (!isAuthenticated && !isAuthRoute) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  return <>{children}</>;
}
