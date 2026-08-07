"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store/auth-store";
import { useRouter } from "next/navigation";
import { Loader2, Eye, EyeOff, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export function LoginForm() {
  const { login } = useAuthStore();
  const router = useRouter();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const isNoAccountError = errorMsg?.toLowerCase().includes("no account found");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsLoading(true);
    try {
      await login(email, password, rememberMe);
      router.push("/");
    } catch (err: any) {
      if (err.status === 401 || err.status === 403) {
        setErrorMsg("Incorrect email or password.");
      } else if (err.status === 404 || err.message?.toLowerCase().includes("not found")) {
        setErrorMsg("No account found. Please sign up first.");
      } else if (!err.status) {
        setErrorMsg("Network error. Please try again later.");
      } else {
        setErrorMsg(err.message || "Failed to sign in. Please try again.");
      }
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
            onChange={e => { setEmail(e.target.value); setErrorMsg(null); }}
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
          <div className="relative">
            <input 
              type={showPassword ? "text" : "password"} 
              required
              value={password}
              onChange={e => { setPassword(e.target.value); setErrorMsg(null); }}
              className="w-full h-11 pl-4 pr-10 rounded-xl bg-background border border-border/10 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all text-sm text-foreground"
              placeholder="••••••••"
            />
            <button 
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <div className="flex items-center space-x-2 ml-1">
          <input 
            type="checkbox" 
            id="rememberMe"
            checked={rememberMe}
            onChange={e => setRememberMe(e.target.checked)}
            className="rounded border-border/20 text-cyan-500 focus:ring-cyan-500/50 bg-background"
          />
          <label htmlFor="rememberMe" className="text-xs text-muted-foreground cursor-pointer">
            Remember me
          </label>
        </div>

        {/* Inline error banner */}
        {errorMsg && (
          <div className="flex items-start gap-2.5 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>
              {errorMsg}
              {isNoAccountError && (
                <>
                  {" "}
                  <Link href="/register" className="underline underline-offset-2 font-medium text-red-300 hover:text-red-200">
                    Sign up here.
                  </Link>
                </>
              )}
            </span>
          </div>
        )}

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
