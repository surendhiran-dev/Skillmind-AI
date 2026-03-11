import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AvatarPanel = ({ state = 'IDLE', isDocked = false }) => {
  // state: 'IDLE', 'SPEAKING', 'LISTENING', 'THINKING', 'COMPLETE'
  const [blink, setBlink] = useState(false);

  useEffect(() => {
    const blinkInterval = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 200);
    }, 4000);
    return () => clearInterval(blinkInterval);
  }, []);

  return (
    <div className={`relative w-full flex items-center justify-center overflow-hidden transition-all duration-500 ${
      isDocked ? 'h-full bg-transparent border-none shadow-none' : 'h-[500px] rounded-3xl bg-glass border border-glass-border shadow-neon'
    }`}>
      <AnimatePresence mode="wait">
        <motion.div
          key="avatar"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className={`relative ${isDocked ? 'w-48 h-48' : 'w-64 h-64'}`}
        >
          {/* Subtle Float Animation */}
          <motion.svg
            viewBox="0 0 200 200"
            className="w-full h-full"
            animate={{ translateY: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          >
            {/* Background Glow */}
            <defs>
              <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(0, 212, 255, 0.2)" />
                <stop offset="100%" stopColor="rgba(0, 212, 255, 0)" />
              </radialGradient>
            </defs>
            <circle cx="100" cy="100" r="90" fill="url(#glow)" />

            {/* Face/Head */}
            <circle cx="100" cy="80" r="50" fill="#2d3436" stroke="#00d4ff" strokeWidth="2" />
            
            {/* Professional Attire */}
            <path 
              d="M50 140 Q100 110 150 140 L160 180 Q100 200 40 180 Z" 
              fill="#1e272e" 
              stroke="#00d4ff" 
              strokeWidth="2" 
            />
            <path d="M100 110 L90 140 L100 150 L110 140 Z" fill="#34495e" /> {/* Tie */}

            {/* Eyes */}
            <g transform="translate(100, 75)">
              <motion.ellipse 
                cx="-20" cy="0" rx="6" ry={blink ? 1 : 6} 
                fill="#00d4ff" 
              />
              <motion.ellipse 
                cx="20" cy="0" rx="6" ry={blink ? 1 : 6} 
                fill="#00d4ff" 
              />
            </g>

            {/* Mouth */}
            <motion.path
              d={state === 'SPEAKING' ? "M85 105 Q100 120 115 105" : "M85 110 Q100 110 115 110"}
              fill="none"
              stroke="#00d4ff"
              strokeWidth="3"
              strokeLinecap="round"
              animate={state === 'SPEAKING' ? { 
                d: ["M85 110 Q100 110 115 110", "M85 105 Q100 125 115 105", "M85 110 Q100 110 115 110"],
              } : state === 'COMPLETE' ? {
                d: "M80 105 Q100 125 120 105" // Smile
              } : {}}
              transition={state === 'SPEAKING' ? {
                duration: 0.3,
                repeat: Infinity
              } : {}}
            />

            {/* Thinking Ellipsis */}
            {state === 'THINKING' && (
              <g transform="translate(140, 50)">
                <motion.circle cx="0" cy="0" r="3" fill="#00d4ff" animate={{ opacity: [0, 1, 0] }} transition={{ duration: 1, repeat: Infinity, delay: 0 }} />
                <motion.circle cx="10" cy="0" r="3" fill="#00d4ff" animate={{ opacity: [0, 1, 0] }} transition={{ duration: 1, repeat: Infinity, delay: 0.3 }} />
                <motion.circle cx="20" cy="0" r="3" fill="#00d4ff" animate={{ opacity: [0, 1, 0] }} transition={{ duration: 1, repeat: Infinity, delay: 0.6 }} />
              </g>
            )}
          </motion.svg>
        </motion.div>
      </AnimatePresence>

      {/* Status Overlay (Only in full view) */}
      {!isDocked && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-3 px-4 py-2 bg-black/40 backdrop-blur-md rounded-full border border-white/10">
          <div className={`w-3 h-3 rounded-full ${
            state === 'SPEAKING' ? 'bg-green-400 animate-pulse' : 
            state === 'LISTENING' ? 'bg-red-400 animate-pulse' : 
            state === 'THINKING' ? 'bg-yellow-400' : 'bg-blue-400'
          }`} />
          <span className="text-xs font-bold tracking-widest text-white/80 uppercase">
            {state}
          </span>
        </div>
      )}
    </div>
  );
};

export default AvatarPanel;
