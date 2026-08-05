import React from "react";

// Pre-generated static positions for 25 particles to avoid hydration mismatches
// and expensive re-renders. (Top %, Left %, Delay s, Duration s, Scale)
const PARTICLES = [
  { top: 15, left: 20, delay: 0.5, dur: 15, scale: 1 },
  { top: 25, left: 75, delay: 2.1, dur: 18, scale: 0.8 },
  { top: 40, left: 10, delay: 1.2, dur: 14, scale: 1.2 },
  { top: 60, left: 85, delay: 3.5, dur: 16, scale: 0.9 },
  { top: 80, left: 30, delay: 0.8, dur: 17, scale: 1.1 },
  { top: 10, left: 50, delay: 4.2, dur: 15, scale: 0.7 },
  { top: 90, left: 70, delay: 1.9, dur: 19, scale: 1.3 },
  { top: 35, left: 90, delay: 2.5, dur: 14, scale: 0.85 },
  { top: 55, left: 15, delay: 0.2, dur: 16, scale: 1.05 },
  { top: 75, left: 55, delay: 3.8, dur: 18, scale: 0.95 },
  { top: 20, left: 40, delay: 1.5, dur: 15, scale: 1.15 },
  { top: 85, left: 10, delay: 5.1, dur: 17, scale: 0.75 },
  { top: 50, left: 45, delay: 2.8, dur: 16, scale: 1.25 },
  { top: 5, left: 80, delay: 0.9, dur: 14, scale: 0.8 },
  { top: 65, left: 65, delay: 4.5, dur: 19, scale: 1.1 },
  { top: 30, left: 5, delay: 1.8, dur: 15, scale: 0.9 },
  { top: 45, left: 95, delay: 3.2, dur: 18, scale: 1 },
  { top: 95, left: 40, delay: 0.4, dur: 16, scale: 1.2 },
  { top: 12, left: 60, delay: 2.2, dur: 14, scale: 0.85 },
  { top: 70, left: 25, delay: 5.5, dur: 17, scale: 1.05 },
  { top: 88, left: 88, delay: 1.1, dur: 15, scale: 0.95 },
  { top: 42, left: 35, delay: 3.9, dur: 19, scale: 1.15 },
  { top: 28, left: 68, delay: 0.7, dur: 16, scale: 0.75 },
  { top: 78, left: 82, delay: 2.4, dur: 14, scale: 1.25 },
  { top: 52, left: 22, delay: 4.8, dur: 18, scale: 0.8 }
];

export function AmbientBackground() {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10 bg-background select-none">
      
      {/* 1. Subtle Grid Texture (High contrast, respects reduced motion implicitly as it is static) */}
      <div 
        className="absolute inset-0 opacity-[0.015] dark:opacity-[0.03]"
        style={{
          backgroundImage: `linear-gradient(to right, #888 1px, transparent 1px), linear-gradient(to bottom, #888 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }}
      />

      {/* 2. Large Glowing Orbs (Upper Right) */}
      {/* Orb 1: Cyan/Blue Primary */}
      <div 
        className="absolute top-[-20%] right-[-10%] w-[80vw] h-[80vw] md:w-[60vw] md:h-[60vw] rounded-full bg-cyan-500/20 dark:bg-cyan-400/15 blur-[120px] md:blur-[180px] mix-blend-screen animate-float-orb"
        style={{ willChange: 'transform' }}
      />
      
      {/* Orb 2: Deep Blue Secondary */}
      <div 
        className="absolute top-[5%] right-[10%] w-[60vw] h-[60vw] md:w-[45vw] md:h-[45vw] rounded-full bg-blue-600/20 dark:bg-blue-500/15 blur-[100px] md:blur-[150px] mix-blend-screen animate-float-orb-reverse"
        style={{ willChange: 'transform', animationDelay: '-15s' }}
      />

      {/* Orb 3: Magenta/Purple Overlap Glow */}
      <div 
        className="absolute top-[15%] right-[0%] w-[40vw] h-[40vw] md:w-[30vw] md:h-[30vw] rounded-full bg-purple-500/15 dark:bg-fuchsia-500/10 blur-[90px] md:blur-[140px] mix-blend-screen animate-float-orb"
        style={{ willChange: 'transform', animationDelay: '-7s' }}
      />

      {/* 3. Sparse Particle Field */}
      <div className="absolute inset-0">
        {PARTICLES.map((p, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-cyan-400 dark:bg-cyan-300 mix-blend-screen animate-drift-particle"
            style={{
              top: `${p.top}%`,
              left: `${p.left}%`,
              width: `${p.scale * 3}px`,
              height: `${p.scale * 3}px`,
              animationDelay: `${p.delay}s`,
              animationDuration: `${p.dur}s`,
              willChange: 'transform, opacity'
            }}
          />
        ))}
      </div>

    </div>
  );
}
