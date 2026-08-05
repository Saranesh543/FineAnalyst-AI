"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store/auth-store";
import { authClient } from "@/lib/api/auth-client";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { toast } from "sonner";

export function RegisterForm() {
  const { login } = useAuthStore();
  const router = useRouter();
  
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await authClient.register(name, email, password);
      login(res.user, res.accessToken);
      toast.success("Account created successfully!");
      router.push("/");
    } catch (err: any) {
      toast.error(err.message || "Failed to register");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md p-8 rounded-2xl bg-card/40 backdrop-blur-md border border-border/20 shadow-glow mx-auto">
      <div className="flex flex-col items-center space-y-2 mb-8">
        <div className="text-2xl font-semibold flex items-center gap-1 tracking-tight">
          <span>Join</span><span className="text-cyan-400">FineAnalyst</span>
        </div>
        <p className="text-muted-foreground text-sm font-light">Create an account to start analyzing</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground ml-1">Name</label>
          <input 
            type="text" 
            required
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full h-11 px-4 rounded-xl bg-background border border-border/10 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all text-sm text-foreground"
            placeholder="John Doe"
          />
        </div>

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
          <label className="text-xs font-medium text-muted-foreground ml-1">Password</label>
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
          disabled={isLoading || !email || !password || !name}
          className="w-full h-11 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-black shadow-[0_0_15px_rgba(34,211,238,0.2)] font-medium transition-all"
        >
          {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Create Account"}
        </Button>
      </form>

      <div className="mt-6 text-center text-xs text-muted-foreground">
        Already have an account?{" "}
        <Link href="/login" className="text-cyan-400 hover:text-cyan-300 font-medium">
          Sign in
        </Link>
      </div>
    </div>
  );
}
