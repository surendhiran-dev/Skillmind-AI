import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const AriaAvatar = ({ state = 'idle', size = 300, hideStatus = false }) => {
  // Map internal state to user's class-based states
  // User's code uses: idle, speaking, thinking, listening
  const [teethOpacity, setTeethOpacity] = useState(0);

  useEffect(() => {
    let interval;
    if (state === 'speaking') {
      interval = setInterval(() => {
        setTeethOpacity(prev => prev === 0 ? 0.88 : 0);
      }, 200);
    } else {
      setTeethOpacity(0);
    }
    return () => clearInterval(interval);
  }, [state]);

  const labels = {
    idle: 'ARIA · Senior HR Interviewer · Online',
    speaking: '🔊 ARIA is Speaking...',
    thinking: '💭 ARIA is Thinking...',
    listening: '👂 ARIA is Listening...'
  };

  const dotColors = {
    idle: '#1a73e8',
    speaking: '#34a853',
    thinking: '#fbbc04',
    listening: '#4fc3f7'
  };

  return (
    <div className={`aria-avatar-container flex flex-col items-center gap-6 select-none`}>
      <style>{`
        /* ── AVATAR WRAP ── */
        .aw { position: relative; width: ${size}px; height: ${size}px; display: flex; align-items: center; justify-content: center; transform: scale(${size/290}); }
        .spin-ring {
          position: absolute; inset: -7px; border-radius: 50%;
          background: conic-gradient(from 0deg, #1a73e8 0%, #0d47a1 22%, #0a2d6e 38%, #1a73e8 52%, #4fc3f7 68%, #1a73e8 100%);
          padding: 3px; animation: spinRing 6s linear infinite;
        }
        .spin-ring-inner { width: 100%; height: 100%; border-radius: 50%; background: #07080d; }
        @keyframes spinRing { to { transform: rotate(360deg); } }

        .pulse-ring {
          position: absolute; inset: -3px; border-radius: 50%;
          border: 2.5px solid rgba(26,115,232,0.5);
          display: none;
          animation: pulseGlow 1.4s ease-in-out infinite;
        }
        @keyframes pulseGlow { 0%, 100% { transform: scale(1); opacity: 0.7; } 50% { transform: scale(1.05); opacity: 0.2; } }

        .ac {
          width: 270px; height: 270px; border-radius: 50%; overflow: hidden;
          position: relative; z-index: 2;
          box-shadow: 0 24px 64px rgba(0,0,0,0.8), 0 0 0 1px rgba(26,115,232,0.12), inset 0 0 40px rgba(0,0,0,0.4);
        }

        /* IDLE STATE */
        .aw.idle .body-group  { animation: idleFloat 3.8s ease-in-out infinite; }
        .aw.idle .eye-l       { animation: blinkEye 5.5s ease-in-out infinite; transform-origin: center; }
        .aw.idle .eye-r       { animation: blinkEye 5.5s ease-in-out .12s infinite; transform-origin: center; }
        .aw.idle .chin-arm    { opacity: 0; transform: translateY(60px); }
        .aw.idle .think-dots, .aw.idle .think-bubble { opacity: 0; }

        @keyframes idleFloat { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-9px) } }
        @keyframes blinkEye { 0%, 85%, 100% { transform: scaleY(1); } 90%, 94% { transform: scaleY(0.06); } }

        /* SPEAKING STATE */
        .aw.speaking .body-group { animation: speakFloat 0.9s ease-in-out infinite; }
        .aw.speaking .pulse-ring { display: block; }
        .aw.speaking .eye-l { animation: blinkEye 5.5s ease-in-out infinite; transform-origin: center; }
        .aw.speaking .eye-r { animation: blinkEye 5.5s ease-in-out 0.12s infinite; transform-origin: center; }
        .aw.speaking .chin-arm, .aw.speaking .think-dots, .aw.speaking .think-bubble { opacity: 0; }
        @keyframes speakFloat { 0%, 100% { transform: translateY(0) } 50% { transform: translateY(-4px) } }

        /* LISTENING STATE */
        .aw.listening .body-group { animation: idleFloat 3s ease-in-out infinite; }
        .aw.listening .eye-l { animation: blinkEye 4s ease-in-out infinite; transform-origin: center; }
        .aw.listening .eye-r { animation: blinkEye 4s ease-in-out 0.1s infinite; transform-origin: center; }
        .aw.listening .chin-arm, .aw.listening .think-dots, .aw.listening .think-bubble { opacity: 0; }

        /* THINKING STATE */
        .aw.thinking .body-group { animation: thinkTilt 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; transform-origin: 150px 200px; }
        @keyframes thinkTilt {
          0% { transform: translateY(0) rotate(0deg); }
          15% { transform: translateY(-6px) rotate(2.5deg); }
          45% { transform: translateY(-8px) rotate(2deg); }
          55% { transform: translateY(-8px) rotate(2.5deg); }
          85% { transform: translateY(-5px) rotate(1.5deg); }
          100% { transform: translateY(0) rotate(0deg); }
        }
        .aw.thinking .iris-grp-l { animation: eyeLookUpL 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; transform-origin: 118px 122px; }
        .aw.thinking .iris-grp-r { animation: eyeLookUpR 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; transform-origin: 182px 122px; }
        @keyframes eyeLookUpL { 0%, 100% { transform: translate(0, 0); } 20%, 80% { transform: translate(-3px, -4px); } 50% { transform: translate(-2px, -5px); } }
        @keyframes eyeLookUpR { 0%, 100% { transform: translate(0, 0); } 20%, 80% { transform: translate(-3px, -4px); } 50% { transform: translate(-2px, -5px); } }
        .aw.thinking .eye-l { animation: thinkLid 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; transform-origin: 118px 122px; }
        .aw.thinking .eye-r { animation: thinkLid 4s cubic-bezier(0.4, 0, 0.2, 1) infinite 0.06s; transform-origin: 182px 122px; }
        @keyframes thinkLid { 0%, 100% { transform: scaleY(1); } 10% { transform: scaleY(0.55); } 18% { transform: scaleY(0.85); } 45%, 65% { transform: scaleY(0.78); } 75% { transform: scaleY(0.55); } 82% { transform: scaleY(0.88); } }
        .aw.thinking .brow-l-el { animation: browLift 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; transform-origin: 118px 104px; }
        @keyframes browLift { 0%, 100% { transform: translate(0, 0) rotate(0deg); } 20%, 80% { transform: translate(0, -3px) rotate(-2deg); } 50% { transform: translate(0, -4px) rotate(-2.5deg); } }
        .aw.thinking .mouth-el { animation: mouthPurse 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
        @keyframes mouthPurse {
          0%, 100% { d: path('M 132 168 Q 141 174 150 175 Q 159 174 168 168'); }
          25%, 75% { d: path('M 136 168 Q 141 170 150 171 Q 159 170 164 168'); }
          50% { d: path('M 137 167 Q 141 169 150 170 Q 159 169 163 167'); }
        }
        .aw.thinking .chin-arm { animation: armRise 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; transform-origin: 60px 340px; }
        @keyframes armRise { 0% { opacity: 0; transform: translateY(70px) rotate(8deg); } 12% { opacity: 1; transform: translateY(20px) rotate(4deg); } 20%, 80% { opacity: 1; transform: translateY(0) rotate(0deg); } 88% { opacity: 1; transform: translateY(15px) rotate(3deg); } 100% { opacity: 0; transform: translateY(70px) rotate(8deg); } }
        .aw.thinking .chin-tap { animation: chinTap 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
        @keyframes chinTap { 0%, 19%, 100% { transform: translateY(0); } 30% { transform: translateY(-3px); } 37% { transform: translateY(0); } 50% { transform: translateY(-4px); } 57% { transform: translateY(0); } 70% { transform: translateY(-2px); } 76% { transform: translateY(0); } }
        .aw.thinking .think-bubble { animation: bubbleFade 4s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
        @keyframes bubbleFade { 0%, 10% { opacity: 0; transform: scale(0.7) translateY(8px); } 25%, 75% { opacity: 1; transform: scale(1) translateY(0); } 90%, 100% { opacity: 0; transform: scale(0.7) translateY(8px); } }
        .aw.thinking .td1 { animation: tdot 1s ease-in-out infinite 0s; }
        .aw.thinking .td2 { animation: tdot 1s ease-in-out infinite 0.22s; }
        .aw.thinking .td3 { animation: tdot 1s ease-in-out infinite 0.44s; }
        @keyframes tdot { 0%, 100% { transform: translateY(0); opacity: 0.4; } 45% { transform: translateY(-6px); opacity: 1; } }

        /* STATUS DOT */
        .s-dot { width: 7px; height: 7px; border-radius: 50%; animation: dp 1.8s ease-in-out infinite; }
        @keyframes dp { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.3; transform: scale(0.7); } }
      `}</style>

      {/* ── AVATAR WRAP ── */}
      <div className={`aw ${state}`} id="ariaWrap">
        <div className="spin-ring"><div className="spin-ring-inner"></div></div>
        <div className="pulse-ring"></div>
        <div className="ac">
          <svg viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg" width="270" height="270">
            <defs>
              <radialGradient id="bgM" cx="50%" cy="38%" r="65%">
                <stop offset="0%" stopColor="#0d1e3d"/><stop offset="100%" stopColor="#050d1c"/>
              </radialGradient>
              <radialGradient id="skinM" cx="44%" cy="34%" r="68%">
                <stop offset="0%" stopColor="#f2c898"/><stop offset="60%" stopColor="#dba06a"/><stop offset="100%" stopColor="#c88048"/>
              </radialGradient>
              <radialGradient id="skinD" cx="44%" cy="34%" r="68%">
                <stop offset="0%" stopColor="#e0a860"/><stop offset="100%" stopColor="#b87840"/>
              </radialGradient>
              <radialGradient id="hairM" cx="50%" cy="25%" r="75%">
                <stop offset="0%" stopColor="#1e1008"/><stop offset="100%" stopColor="#080402"/>
              </radialGradient>
              <radialGradient id="irisM" cx="32%" cy="32%" r="62%">
                <stop offset="0%" stopColor="#4a90d4"/><stop offset="40%" stopColor="#1e5ca8"/><stop offset="100%" stopColor="#0a2a5e"/>
              </radialGradient>
              <linearGradient id="suitM" x1="0" y1="0" x2="0.3" y2="1">
                <stop offset="0%" stopColor="#162444"/><stop offset="100%" stopColor="#080e1e"/>
              </linearGradient>
              <linearGradient id="shirtM" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#eef2fa"/><stop offset="100%" stopColor="#d0d8f0"/>
              </linearGradient>
              <linearGradient id="tieM" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1a73e8"/><stop offset="50%" stopColor="#0d47a1"/><stop offset="100%" stopColor="#072060"/>
              </linearGradient>
              <radialGradient id="blushM" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#d08050" stopOpacity="0.25"/>
                <stop offset="100%" stopColor="#d08050" stopOpacity="0"/>
              </radialGradient>
              <clipPath id="mainC"><circle cx="150" cy="150" r="150"/></clipPath>
              <filter id="fShad"><feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#000" floodOpacity="0.4"/></filter>
            </defs>

            <g clipPath="url(#mainC)">
              <circle cx="150" cy="150" r="150" fill="url(#bgM)"/>
              <g opacity="0.04" stroke="#4a8ef7" strokeWidth="0.6">
                <line x1="0" y1="50" x2="300" y2="50"/> <line x1="0" y1="100" x2="300" y2="100"/>
                <line x1="0" y1="150" x2="300" y2="150"/> <line x1="0" y1="200" x2="300" y2="200"/>
                <line x1="0" y1="250" x2="300" y2="250"/>
                <line x1="50" y1="0" x2="50" y2="300"/> <line x1="100" y1="0" x2="100" y2="300"/>
                <line x1="150" y1="0" x2="150" y2="300"/> <line x1="200" y1="0" x2="200" y2="300"/>
                <line x1="250" y1="0" x2="250" y2="300"/>
              </g>

              <g className="body-group">
                {/* THINKING BUBBLE */}
                <g className="think-bubble" style={{ transformOrigin: '215px 72px' }}>
                  <ellipse cx="217" cy="75" rx="33" ry="22" fill="#000" opacity="0.25"/>
                  <ellipse cx="215" cy="72" rx="32" ry="21" fill="#0d1e3d" stroke="rgba(26,115,232,0.5)" strokeWidth="1.5"/>
                  <circle cx="192" cy="90" r="4" fill="#0d1e3d" stroke="rgba(26,115,232,0.4)" strokeWidth="1.2"/>
                  <circle cx="184" cy="100" r="2.8" fill="#0d1e3d" stroke="rgba(26,115,232,0.35)" strokeWidth="1"/>
                  <circle cx="178" cy="108" r="1.8" fill="#0d1e3d" stroke="rgba(26,115,232,0.3)" strokeWidth="0.8"/>
                  <circle className="td1" cx="203" cy="72" r="4.5" fill="#1a73e8" style={{ transformOrigin: '203px 72px' }}/>
                  <circle className="td2" cx="215" cy="72" r="4.5" fill="#4fc3f7" style={{ transformOrigin: '215px 72px' }}/>
                  <circle className="td3" cx="227" cy="72" r="4.5" fill="#1a73e8" style={{ transformOrigin: '227px 72px' }}/>
                </g>

                <ellipse cx="150" cy="308" rx="108" ry="58" fill="url(#suitM)"/>
                <path d="M 44 355 L 52 210 Q 82 188 124 182 L 146 285 Z" fill="url(#suitM)"/>
                <path d="M 256 355 L 248 210 Q 218 188 176 182 L 154 285 Z" fill="url(#suitM)"/>
                <path d="M 124 182 L 146 285 L 154 285 L 176 182 Q 163 176 150 175 Q 137 176 124 182 Z" fill="url(#shirtM)"/>
                <path d="M 144 184 L 150 193 L 156 184 L 153 180 L 147 180 Z" fill="url(#tieM)"/>
                <path d="M 146 193 L 150 278 L 154 193 Z" fill="url(#tieM)"/>
                <path d="M 149 196 L 150 244 L 151 196 Z" fill="white" opacity="0.1"/>
                <rect x="146" y="232" width="8" height="3" rx="1.5" fill="#c8d4f0" opacity="0.65"/>
                <path d="M 124 182 L 134 228 L 146 212 L 146 190 Z" fill="#0e1c3a"/>
                <path d="M 176 182 L 166 228 L 154 212 L 154 190 Z" fill="#0e1c3a"/>
                <path d="M 66 212 L 84 212 L 84 222 L 80 218 L 75 222 L 70 218 L 66 222 Z" fill="#1a73e8" opacity="0.72"/>
                <path d="M 66 212 L 84 212 L 84 214 L 66 214 Z" fill="#4fc3f7" opacity="0.55"/>
                <circle cx="80" cy="226" r="5" fill="#1a73e8" opacity="0.8"/>
                <circle cx="80" cy="226" r="2.5" fill="#4fc3f7" opacity="0.9"/>
                <circle cx="150" cy="266" r="3.5" fill="#0e1c3a" stroke="#2a3a60" strokeWidth="1"/>

                {/* CHIN FINGER ARM */}
                <g className="chin-arm">
                  <g className="chin-tap" style={{ transformOrigin: '152px 210px' }}>
                    <path d="M 52 355 Q 72 295 105 262 Q 118 250 130 244" stroke="#162444" strokeWidth="26" fill="none" strokeLinecap="round"/>
                    <path d="M 118 252 Q 128 245 138 242" stroke="#d0d8f0" strokeWidth="10" fill="none" strokeLinecap="round"/>
                    <ellipse cx="144" cy="238" rx="20" ry="15" fill="url(#skinM)" transform="rotate(-10,144,238)"/>
                    <path d="M 127 233 Q 130 222 136 220 Q 140 219 141 226 Q 138 232 136 238" fill="url(#skinM)" stroke="#c88048" strokeWidth="0.5"/>
                    <path d="M 134 230 Q 136 218 143 216 Q 147 215 148 223 Q 146 229 144 235" fill="url(#skinM)" stroke="#c88048" strokeWidth="0.5"/>
                    <path d="M 141 228 Q 143 218 149 217 Q 153 217 153 224 Q 152 229 151 234" fill="url(#skinM)" stroke="#c88048" strokeWidth="0.5"/>
                    <path d="M 148 238 Q 150 228 151 215 Q 152 208 153 204 Q 154 200 155 196" stroke="url(#skinM)" strokeWidth="11" fill="none" strokeLinecap="round"/>
                    <ellipse cx="155" cy="194" rx="6" ry="7" fill="#f2c898"/>
                    <ellipse cx="155" cy="190" rx="3.5" ry="4" fill="#e8d0b8" opacity="0.7"/>
                    <path d="M 150 222 Q 154 220 156 222" stroke="#c88048" strokeWidth="1" fill="none" opacity="0.5"/>
                    <path d="M 151 212 Q 155 210 157 212" stroke="#c88048" strokeWidth="1" fill="none" opacity="0.4"/>
                    <path d="M 128 238 Q 124 244 126 250 Q 130 254 136 250" fill="url(#skinM)" stroke="#c88048" strokeWidth="0.6"/>
                  </g>
                </g>

                <rect x="133" y="162" width="34" height="26" rx="7" fill="url(#skinM)" filter="url(#fShad)"/>
                <rect x="133" y="162" width="7" height="26" rx="4" fill="#a07040" opacity="0.22"/>
                <rect x="160" y="162" width="7" height="26" rx="4" fill="#a07040" opacity="0.22"/>
                <ellipse cx="150" cy="122" rx="57" ry="61" fill="url(#skinM)" filter="url(#fShad)"/>
                <ellipse cx="93" cy="128" rx="10" ry="15" fill="url(#skinD)"/>
                <ellipse cx="207" cy="128" rx="10" ry="15" fill="url(#skinD)"/>
                <ellipse cx="94" cy="128" rx="5.5" ry="9" fill="url(#skinM)"/>
                <ellipse cx="206" cy="128" rx="5.5" ry="9" fill="url(#skinM)"/>
                <ellipse cx="94" cy="130" rx="2.5" ry="4" fill="#b87840" opacity="0.45"/>
                <ellipse cx="206" cy="130" rx="2.5" ry="4" fill="#b87840" opacity="0.45"/>
                <ellipse cx="150" cy="72" rx="55" ry="26" fill="url(#hairM)"/>
                <ellipse cx="150" cy="68" rx="48" ry="20" fill="#1a0e08"/>
                <ellipse cx="95" cy="100" rx="15" ry="30" fill="url(#hairM)"/>
                <ellipse cx="205" cy="100" rx="15" ry="30" fill="url(#hairM)"/>
                <path d="M 100 84 Q 115 68 135 70 Q 148 66 162 70 Q 178 68 196 82 Q 178 74 162 76 Q 148 72 135 76 Q 118 74 100 84 Z" fill="#2a1810" opacity="0.6"/>
                <path d="M 108 80 Q 118 72 130 76 Q 120 82 108 88 Z" fill="#301808" opacity="0.5"/>
                <ellipse cx="138" cy="73" rx="18" ry="7" fill="#382010" opacity="0.52"/>

                <g className="brow-l-el">
                  <path d="M 104 107 Q 116 100 132 104" stroke="#1e0e06" strokeWidth="5.5" fill="none" strokeLinecap="round"/>
                  <path d="M 104 107 Q 116 101 132 105" stroke="#2e1808" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.4"/>
                </g>
                <path d="M 168 104 Q 184 100 196 107" stroke="#1e0e06" strokeWidth="5.5" fill="none" strokeLinecap="round"/>
                <path d="M 168 105 Q 184 101 196 108" stroke="#2e1808" strokeWidth="2" fill="none" strokeLinecap="round" opacity="0.4"/>

                <ellipse cx="118" cy="120" rx="18" ry="14" fill="#a06030" opacity="0.12"/>
                <ellipse cx="182" cy="120" rx="18" ry="14" fill="#a06030" opacity="0.12"/>

                <g className="eye-l" style={{ transformOrigin: '118px 122px' }}>
                  <ellipse cx="118" cy="122" rx="15" ry="12" fill="#f8f8f8"/>
                  <g className="iris-grp-l">
                    <ellipse cx="118" cy="122" rx="11" ry="11" fill="url(#irisM)"/>
                    <circle cx="118" cy="122" r="7" fill="#060e1c"/>
                    <circle cx="121.5" cy="119" r="3.2" fill="white" opacity="0.92"/>
                    <circle cx="115" cy="125" r="1.4" fill="white" opacity="0.4"/>
                    <circle cx="118" cy="122" r="11" fill="none" stroke="#0a2a5e" strokeWidth="0.7" opacity="0.55"/>
                  </g>
                  <path d="M 103 115 Q 118 108 133 115" stroke="#1a0808" strokeWidth="2.2" fill="none" strokeLinecap="round"/>
                  <line x1="104" y1="116" x2="101" y2="111" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="110" y1="111" x2="108" y2="106" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="118" y1="108" x2="118" y2="103" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="126" y1="110" x2="127" y2="105" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="132" y1="115" x2="135" y2="111" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <path d="M 104 129 Q 118 134 132 129" stroke="#a06040" strokeWidth="0.7" fill="none" opacity="0.3"/>
                </g>

                <g className="eye-r" style={{ transformOrigin: '182px 122px' }}>
                  <ellipse cx="182" cy="122" rx="15" ry="12" fill="#f8f8f8"/>
                  <g className="iris-grp-r">
                    <ellipse cx="182" cy="122" rx="11" ry="11" fill="url(#irisM)"/>
                    <circle cx="182" cy="122" r="7" fill="#060e1c"/>
                    <circle cx="185.5" cy="119" r="3.2" fill="white" opacity="0.92"/>
                    <circle cx="179" cy="125" r="1.4" fill="white" opacity="0.4"/>
                    <circle cx="182" cy="122" r="11" fill="none" stroke="#0a2a5e" strokeWidth="0.7" opacity="0.55"/>
                  </g>
                  <path d="M 167 115 Q 182 108 197 115" stroke="#1a0808" strokeWidth="2.2" fill="none" strokeLinecap="round"/>
                  <line x1="168" y1="116" x2="165" y2="111" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="174" y1="111" x2="172" y2="106" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="182" y1="108" x2="182" y2="103" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="190" y1="110" x2="191" y2="105" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <line x1="196" y1="115" x2="199" y2="111" stroke="#140806" strokeWidth="1.6" strokeLinecap="round"/>
                  <path d="M 168 129 Q 182 134 196 129" stroke="#a06040" strokeWidth="0.7" fill="none" opacity="0.3"/>
                </g>

                <path d="M 147 127 Q 143 140 141 154" stroke="#b07840" strokeWidth="1.3" fill="none" opacity="0.38"/>
                <path d="M 153 127 Q 157 140 159 154" stroke="#b07840" strokeWidth="1.3" fill="none" opacity="0.38"/>
                <path d="M 150 130 L 141 153 Q 150 160 159 153 Z" fill="#b07848" opacity="0.46"/>
                <ellipse cx="141" cy="155" rx="7" ry="4.5" fill="#b07848" opacity="0.4"/>
                <ellipse cx="159" cy="155" rx="7" ry="4.5" fill="#b07848" opacity="0.4"/>
                <ellipse cx="140" cy="157" rx="4.5" ry="2.8" fill="#804020" opacity="0.32"/>
                <ellipse cx="160" cy="157" rx="4.5" ry="2.8" fill="#804020" opacity="0.32"/>

                <ellipse cx="105" cy="146" rx="20" ry="13" fill="url(#blushM)"/>
                <ellipse cx="195" cy="146" rx="20" ry="13" fill="url(#blushM)"/>

                <ellipse cx="150" cy="168" rx="18" ry="5" fill="#806040" opacity="0.17"/>
                <ellipse cx="150" cy="176" rx="30" ry="14" fill="#806040" opacity="0.12"/>
                <ellipse cx="126" cy="170" rx="16" ry="9" fill="#806040" opacity="0.1"/>
                <ellipse cx="174" cy="170" rx="16" ry="9" fill="#806040" opacity="0.1"/>
                <ellipse cx="150" cy="184" rx="20" ry="7" fill="#806040" opacity="0.13"/>

                <path d="M 132 168 Q 141 178 150 179 Q 159 178 168 168 Q 159 174 150 175 Q 141 174 132 168 Z" fill="#c06848" opacity="0.86"/>
                <path className="mouth-el" d="M 132 168 Q 141 174 150 175 Q 159 174 168 168" fill="#c86050" stroke="#d06858" strokeWidth="1.2" opacity="0.82"/>
                <path d="M 132 168 Q 140 164 146 166 Q 150 164 154 166 Q 160 164 168 168" stroke="#d06858" strokeWidth="1" fill="none" opacity="0.5"/>
                <path d="M 130 167 Q 127 161 132 156" stroke="#b05840" strokeWidth="1.1" fill="none" opacity="0.35"/>
                <path d="M 170 167 Q 173 161 168 156" stroke="#b05840" strokeWidth="1.1" fill="none" opacity="0.35"/>
                <path id="teethEl" d="M 136 170 Q 150 176 164 170 L 164 172 Q 150 178 136 172 Z" fill="white" opacity={teethOpacity}/>

                <ellipse cx="150" cy="178" rx="24" ry="9" fill="#050a14" opacity="0.25"/>
                <ellipse cx="150" cy="186" rx="26" ry="6" fill="#050a14" opacity="0.28"/>

              </g>
            </g>

            <defs>
              <linearGradient id="scanG" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#1a73e8" stopOpacity="0"/>
                <stop offset="50%" stopColor="#1a73e8" stopOpacity="1"/>
                <stop offset="100%" stopColor="#1a73e8" stopOpacity="0"/>
              </linearGradient>
            </defs>
            <rect x="0" y="0" width="300" height="1.8" fill="url(#scanG)" opacity="0.28">
              <animate attributeName="y" values="0;300;0" dur="4.5s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values="0.28;0.06;0.28" dur="4.5s" repeatCount="indefinite"/>
            </rect>
            <g stroke="#1a73e8" strokeWidth="2" fill="none" opacity="0.48">
              <path d="M20 8L8 8L8 20"/><path d="M280 8L292 8L292 20"/>
              <path d="M20 292L8 292L8 280"/><path d="M280 292L292 292L292 280"/>
            </g>
            <g fill="#1a73e8" opacity="0.65">
              <circle cx="8" cy="8" r="2"/><circle cx="292" cy="8" r="2"/>
              <circle cx="8" cy="292" r="2"/><circle cx="292" cy="292" r="2"/>
            </g>
            <text x="279" y="22" textAnchor="end" fontSize="7" fill="#1a73e8" opacity="0.5" fontFamily="monospace">AI•HR•v2</text>
            <text x="21" y="282" fontSize="7" fill="#1a73e8" opacity="0.5" fontFamily="monospace">ARIA•LIVE</text>
          </svg>
        </div>
      </div>

      {!hideStatus && (
        <motion.div 
          layout
          className={`px-5 py-2 rounded-full text-[10px] font-black tracking-[0.15em] uppercase flex items-center gap-3 border backdrop-blur-xl shadow-xl z-30 transition-colors duration-500 bg-white/5 border-white/10`}
          style={{ color: '#e8eaed' }}
        >
          <div className="relative">
            <div className={`s-dot`} style={{ background: dotColors[state], boxShadow: `0 0 8px ${dotColors[state]}` }} />
          </div>
          {labels[state]}
        </motion.div>
      )}
    </div>
  );
};

export default AriaAvatar;
