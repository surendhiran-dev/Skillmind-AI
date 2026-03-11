import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const TranscriptPanel = ({ transcript = [], isMinimal = false }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  return (
    <div className={`flex flex-col h-full bg-transparent overflow-hidden ${
      isMinimal ? 'border-none' : 'bg-glass border border-glass-border rounded-3xl'
    }`}>
      {!isMinimal && (
        <div className="p-4 border-b border-glass-border bg-black/20">
          <h3 className="text-sm font-bold tracking-widest text-primary uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            Live Transcript
          </h3>
        </div>
      )}
      
      <div 
        ref={scrollRef}
        className={`flex-1 overflow-y-auto space-y-3 scrollbar-none ${isMinimal ? 'p-2' : 'p-4'}`}
      >
        <AnimatePresence initial={false}>
          {transcript.length === 0 ? (
            <div className={`h-full flex items-center justify-center text-white/30 italic ${isMinimal ? 'text-[10px]' : 'text-sm'}`}>
              Awaiting start...
            </div>
          ) : (
            transcript.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: msg.role === 'ai' ? -10 : 10 }}
                animate={{ opacity: 1, x: 0 }}
                className={`flex flex-col ${msg.role === 'ai' ? 'items-start' : 'items-end'}`}
              >
                <div className={`max-w-[90%] px-3 py-2 rounded-xl border leading-relaxed shadow-lg ${
                  isMinimal ? 'text-[11px]' : 'text-sm'
                } ${
                  msg.role === 'ai' 
                    ? 'bg-blue-600/10 text-blue-100 rounded-tl-none border-blue-500/20' 
                    : 'bg-primary/10 text-white rounded-tr-none border-primary/20'
                }`}>
                  <span className="block text-[8px] font-bold uppercase tracking-widest opacity-40 mb-0.5">
                    {msg.role === 'ai' ? 'AI' : 'You'}
                  </span>
                  {msg.text}
                </div>

                {/* Emotion Badge */}
                {msg.role === 'user' && msg.emotion && (
                  <motion.span 
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="mt-1 px-1.5 py-0.5 rounded-full bg-black/40 text-[8px] font-extrabold uppercase text-primary border border-primary/20"
                  >
                    {msg.emotion}
                  </motion.span>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default TranscriptPanel;
