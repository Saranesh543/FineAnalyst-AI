"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store/auth-store";
import { useRouter } from "next/navigation";
import { Loader2, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { toast } from "sonner";

const getStrength = (pass: string) => {
  let score = 0;
  if (!pass) return { score: 0, text: "", color: "bg-border" };
  if (pass.length > 7) score += 1;
  if (/[A-Z]/.test(pass)) score += 1;
  if (/[a-z]/.test(pass)) score += 1;
  if (/[0-9]/.test(pass)) score += 1;
  if (/[^A-Za-z0-9]/.test(pass)) score += 1;

  if (score < 3) return { score, text: "Weak", color: "bg-red-500" };
  if (score < 5) return { score, text: "Medium", color: "bg-yellow-500" };
  return { score, text: "Strong", color: "bg-green-500" };
};

export function RegisterForm() {
  const { register } = useAuthStore();
  const router = useRouter();
  
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const strength = getStrength(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    
    if (password !== confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    setIsLoading(true);
    try {
      await register(name, email, password);
      toast.success("Account created successfully!");
      router.push("/");
    } catch (err: any) {
      const msg = (err.message || "").toLowerCase();
      const isConflict = err.status === 409 || msg.includes("already exists");
      const isRateLimited = err.status === 429 || msg.includes("too many");

      if (isConflict) {
        toast.error("An account with this email already exists. Please sign in.");
      } else if (isRateLimited) {
        toast.error("Too many attempts. Please wait a moment and try again.");
      } else if (!err.status && !err.message) {
        toast.error("Network error. Please check your connection.");
      } else {
        toast.error(err.message || "Failed to register.");
      }
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
          <div className="relative">
            <input 
              type={showPassword ? "text" : "password"} 
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
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
          {password.length > 0 && (
            <div className="flex items-center gap-2 mt-2 px-1">
              <div className="flex-1 flex h-1 bg-border/50 rounded-full overflow-hidden">
                <div className={`h-full ${strength.color} transition-all duration-300`} style={{ width: `${(strength.score / 5) * 100}%` }} />
              </div>
              <span className="text-[10px] text-muted-foreground">{strength.text}</span>
            </div>
          )}
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground ml-1">Confirm Password</label>
          <div className="relative">
            <input 
              type={showConfirmPassword ? "text" : "password"} 
              required
              value={confirmPassword}
              onChange={e => setConfirmPassword(e.target.value)}
              className="w-full h-11 pl-4 pr-10 rounded-xl bg-background border border-border/10 focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 outline-none transition-all text-sm text-foreground"
              placeholder="••••••••"
            />
            <button 
              type="button"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <Button 
          type="submit" 
          disabled={isLoading || !email || !password || !name || !confirmPassword}
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
