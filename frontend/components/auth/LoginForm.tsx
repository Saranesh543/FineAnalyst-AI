"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store/auth-store";
import { authClient } from "@/lib/api/auth-client";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { toast } from "sonner";

export function LoginForm() {
  const { login } = useAuthStore();
  const router = useRouter();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await authClient.login(email, password);
      login(res.user, res.accessToken);
      toast.success("Welcome back!");
      router.push("/");
    } catch (err: any) {
      toast.error(err.message || "Failed to login");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 rounded-2xl bg-card/40 backdrop-blur-md border border-border/20 shadow-glow mx-auto">
      <div className="flex flex-col items-center space-y-2 mb-8">
        <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-1 justify-center">
          <span>FineAnalyst</span>
        </h1>
        <p className="text-muted-foreground text-sm font-light">Sign in to your account</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground ml-1">Email</label>
          <input 
            type="email" 
            required
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full h-11 px-4 rounded-xl bg-background border border-border/10 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all text-sm text-foreground"
            placeholder="name@example.com"
          />
        </div>

        <div className="space-y-1">
          <div className="flex items-center justify-between ml-1">
            <label className="text-xs font-medium text-muted-foreground">Password</label>
            <Link href="/forgot-password" className="text-[10px] text-cyan-400 hover:text-cyan-300">
              Forgot password?
            </Link>
          </div>
          <input 
            type="password" 
            required
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full h-11 px-4 rounded-xl bg-background border border-border/10 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all text-sm text-foreground"
            placeholder="••••••••"
          />
        </div>

        <Button 
          type="submit" 
          disabled={isLoading || !email || !password}
          className="w-full h-11 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-black shadow-[0_0_15px_rgba(34,211,238,0.2)] font-medium transition-all"
        >
          {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign In"}
        </Button>
      </form>

      <div className="mt-6 text-center text-xs text-muted-foreground">
        Don't have an account?{" "}
        <Link href="/register" className="text-cyan-400 hover:text-cyan-300 font-medium">
          Sign up
        </Link>
      </div>
    </div>
  );
}
