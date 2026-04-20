/**
 * interview_avatar.js — Skill Mind AI
 * ─────────────────────────────────────────────────────────────────
 * REPLACES the broken ReadyPlayer.me / Three.js GLTF avatar loader.
 *
 * This file renders the ARIA SVG avatar directly into whatever
 * container element your HTML points to, with all 4 states:
 *   idle | speaking | thinking | listening
 *
 * HOW TO USE:
 *   1. Drop this file in your frontend/ folder
 *   2. In index.html it is already referenced as:
 *        <script src="interview_avatar.js"></script>
 *   3. The avatar auto-mounts into #iv-avatar-container
 *   4. Control it via:
 *        ARIAAvatar.setState('speaking')
 *        ARIAAvatar.setState('thinking')
 *        ARIAAvatar.setState('listening')
 *        ARIAAvatar.setState('idle')
 *        ARIAAvatar.startMouth()
 *        ARIAAvatar.stopMouth()
 * ─────────────────────────────────────────────────────────────────
 */

const ARIAAvatar = (() => {

  /* ── SVG markup ────────────────────────────────────────────── */
  const SVG_HTML = `
<svg id="ariaSVG" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg"
     width="100%" height="100%" style="border-radius:50%;display:block;">
  <defs>
    <radialGradient id="abg"  cx="50%" cy="38%" r="65%">
      <stop offset="0%"   stop-color="#0d1e3d"/>
      <stop offset="100%" stop-color="#050d1c"/>
    </radialGradient>
    <radialGradient id="ask"  cx="44%" cy="34%" r="68%">
      <stop offset="0%"   stop-color="#f2c898"/>
      <stop offset="60%"  stop-color="#dba06a"/>
      <stop offset="100%" stop-color="#c88048"/>
    </radialGradient>
    <radialGradient id="askd" cx="44%" cy="34%" r="68%">
      <stop offset="0%"   stop-color="#e0a860"/>
      <stop offset="100%" stop-color="#b87840"/>
    </radialGradient>
    <radialGradient id="ah"   cx="50%" cy="25%" r="75%">
      <stop offset="0%"   stop-color="#1e1008"/>
      <stop offset="100%" stop-color="#080402"/>
    </radialGradient>
    <radialGradient id="air"  cx="32%" cy="32%" r="62%">
      <stop offset="0%"   stop-color="#4a90d4"/>
      <stop offset="40%"  stop-color="#1e5ca8"/>
      <stop offset="100%" stop-color="#0a2a5e"/>
    </radialGradient>
    <linearGradient id="asu"  x1="0" y1="0" x2=".3" y2="1">
      <stop offset="0%"   stop-color="#162444"/>
      <stop offset="100%" stop-color="#080e1e"/>
    </linearGradient>
    <linearGradient id="ash"  x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#eef2fa"/>
      <stop offset="100%" stop-color="#d0d8f0"/>
    </linearGradient>
    <linearGradient id="at"   x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%"   stop-color="#1a73e8"/>
      <stop offset="50%"  stop-color="#0d47a1"/>
      <stop offset="100%" stop-color="#072060"/>
    </linearGradient>
    <radialGradient id="abl"  cx="50%" cy="50%" r="50%">
      <stop offset="0%"   stop-color="#d08050" stop-opacity=".22"/>
      <stop offset="100%" stop-color="#d08050" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="scanGL" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%"   stop-color="#1a73e8" stop-opacity="0"/>
      <stop offset="50%"  stop-color="#1a73e8" stop-opacity="1"/>
      <stop offset="100%" stop-color="#1a73e8" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="ariaCP"><circle cx="150" cy="150" r="150"/></clipPath>
  </defs>

  <g clip-path="url(#ariaCP)">
    <!-- background -->
    <circle cx="150" cy="150" r="150" fill="url(#abg)"/>
    <g opacity=".04" stroke="#4a8ef7" stroke-width=".6">
      <line x1="0" y1="75"  x2="300" y2="75"/>
      <line x1="0" y1="150" x2="300" y2="150"/>
      <line x1="0" y1="225" x2="300" y2="225"/>
      <line x1="75"  y1="0" x2="75"  y2="300"/>
      <line x1="150" y1="0" x2="150" y2="300"/>
      <line x1="225" y1="0" x2="225" y2="300"/>
    </g>

    <!-- body group (animated) -->
    <g id="ariaBodyGroup">
      <!-- suit -->
      <ellipse cx="150" cy="308" rx="108" ry="58" fill="url(#asu)"/>
      <path d="M44 355 L52 210 Q82 188 124 182 L146 285 Z" fill="url(#asu)"/>
      <path d="M256 355 L248 210 Q218 188 176 182 L154 285 Z" fill="url(#asu)"/>
      <path d="M124 182 L146 285 L154 285 L176 182 Q163 176 150 175 Q137 176 124 182 Z" fill="url(#ash)"/>
      <!-- tie -->
      <path d="M144 184 L150 193 L156 184 L153 180 L147 180 Z" fill="url(#at)"/>
      <path d="M146 193 L150 278 L154 193 Z" fill="url(#at)"/>
      <rect x="146" y="232" width="8" height="3" rx="1.5" fill="#c8d4f0" opacity=".65"/>
      <!-- lapels -->
      <path d="M124 182 L134 228 L146 212 L146 190 Z" fill="#0e1c3a"/>
      <path d="M176 182 L166 228 L154 212 L154 190 Z" fill="#0e1c3a"/>
      <!-- pocket square -->
      <path d="M66 212 L84 212 L84 222 L80 218 L75 222 L70 218 L66 222 Z" fill="#1a73e8" opacity=".7"/>
      <!-- lapel pin -->
      <circle cx="80" cy="226" r="5"   fill="#1a73e8" opacity=".8"/>
      <circle cx="80" cy="226" r="2.5" fill="#4fc3f7" opacity=".9"/>
      <!-- neck -->
      <rect x="133" y="162" width="34" height="26" rx="7" fill="url(#ask)"/>
      <!-- head -->
      <ellipse cx="150" cy="122" rx="57" ry="61" fill="url(#ask)"/>
      <!-- ears -->
      <ellipse cx="93"  cy="128" rx="10" ry="15" fill="url(#askd)"/>
      <ellipse cx="207" cy="128" rx="10" ry="15" fill="url(#askd)"/>
      <ellipse cx="94"  cy="128" rx="5.5" ry="9" fill="url(#ask)"/>
      <ellipse cx="206" cy="128" rx="5.5" ry="9" fill="url(#ask)"/>
      <!-- hair -->
      <ellipse cx="150" cy="72"  rx="55" ry="26" fill="url(#ah)"/>
      <ellipse cx="150" cy="68"  rx="48" ry="20" fill="#1a0e08"/>
      <ellipse cx="95"  cy="100" rx="15" ry="30" fill="url(#ah)"/>
      <ellipse cx="205" cy="100" rx="15" ry="30" fill="url(#ah)"/>
      <path d="M100 84 Q115 68 135 70 Q148 66 162 70 Q178 68 196 82
               Q178 74 162 76 Q148 72 135 76 Q118 74 100 84 Z"
            fill="#2a1810" opacity=".58"/>
      <ellipse cx="138" cy="73" rx="18" ry="7" fill="#382010" opacity=".5"/>
      <!-- brows -->
      <path d="M104 107 Q116 100 132 104" stroke="#1e0e06" stroke-width="5.5"
            fill="none" stroke-linecap="round"/>
      <path d="M168 104 Q184 100 196 107" stroke="#1e0e06" stroke-width="5.5"
            fill="none" stroke-linecap="round"/>
      <!-- eye sockets -->
      <ellipse cx="118" cy="120" rx="18" ry="14" fill="#a06030" opacity=".11"/>
      <ellipse cx="182" cy="120" rx="18" ry="14" fill="#a06030" opacity=".11"/>

      <!-- LEFT EYE -->
      <g id="ariaEyeL">
        <ellipse cx="118" cy="122" rx="15" ry="12" fill="#f8f8f8"/>
        <g id="ariaIrisL">
          <ellipse cx="118" cy="122" rx="11" ry="11" fill="url(#air)"/>
          <circle  cx="118" cy="122" r="7"   fill="#060e1c"/>
          <circle  cx="121.5" cy="119" r="3.2" fill="white" opacity=".92"/>
          <circle  cx="115"   cy="125" r="1.3" fill="white" opacity=".4"/>
        </g>
        <path d="M103 115 Q118 108 133 115" stroke="#1a0808" stroke-width="2.2"
              fill="none" stroke-linecap="round"/>
        <line x1="104" y1="116" x2="101" y2="111" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="110" y1="111" x2="108" y2="106" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="118" y1="108" x2="118" y2="103" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="126" y1="110" x2="127" y2="105" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="132" y1="115" x2="135" y2="111" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
      </g>

      <!-- RIGHT EYE -->
      <g id="ariaEyeR">
        <ellipse cx="182" cy="122" rx="15" ry="12" fill="#f8f8f8"/>
        <g id="ariaIrisR">
          <ellipse cx="182" cy="122" rx="11" ry="11" fill="url(#air)"/>
          <circle  cx="182" cy="122" r="7"   fill="#060e1c"/>
          <circle  cx="185.5" cy="119" r="3.2" fill="white" opacity=".92"/>
          <circle  cx="179"   cy="125" r="1.3" fill="white" opacity=".4"/>
        </g>
        <path d="M167 115 Q182 108 197 115" stroke="#1a0808" stroke-width="2.2"
              fill="none" stroke-linecap="round"/>
        <line x1="168" y1="116" x2="165" y2="111" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="174" y1="111" x2="172" y2="106" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="182" y1="108" x2="182" y2="103" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="190" y1="110" x2="191" y2="105" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="196" y1="115" x2="199" y2="111" stroke="#140806" stroke-width="1.5" stroke-linecap="round"/>
      </g>

      <!-- nose -->
      <path d="M150 130 L141 153 Q150 160 159 153 Z" fill="#b07848" opacity=".44"/>
      <ellipse cx="141" cy="155" rx="7" ry="4.5" fill="#b07848" opacity=".38"/>
      <ellipse cx="159" cy="155" rx="7" ry="4.5" fill="#b07848" opacity=".38"/>
      <!-- blush -->
      <ellipse cx="105" cy="146" rx="20" ry="13" fill="url(#abl)"/>
      <ellipse cx="195" cy="146" rx="20" ry="13" fill="url(#abl)"/>
      <!-- stubble -->
      <ellipse cx="150" cy="168" rx="18" ry="5"  fill="#806040" opacity=".16"/>
      <ellipse cx="150" cy="176" rx="30" ry="14" fill="#806040" opacity=".11"/>
      <!-- mouth -->
      <path d="M132 168 Q141 178 150 179 Q159 178 168 168
               Q159 174 150 175 Q141 174 132 168 Z"
            fill="#c06848" opacity=".84"/>
      <path d="M132 168 Q141 174 150 175 Q159 174 168 168"
            fill="#c86050" stroke="#d06858" stroke-width="1.2" opacity=".8"/>
      <!-- teeth (shown when speaking) -->
      <path id="ariaTeeth"
            d="M136 170 Q150 176 164 170 L164 172 Q150 178 136 172 Z"
            fill="white" opacity="0"/>
      <!-- mouth dimples -->
      <path d="M130 167 Q127 161 132 156" stroke="#b05840" stroke-width="1" fill="none" opacity=".3"/>
      <path d="M170 167 Q173 161 168 156" stroke="#b05840" stroke-width="1" fill="none" opacity=".3"/>
    </g>
  </g>

  <!-- scan line -->
  <rect x="0" y="0" width="300" height="1.5" fill="url(#scanGL)" opacity=".22">
    <animate attributeName="y" values="0;300;0" dur="4.2s" repeatCount="indefinite"/>
  </rect>
  <!-- corner brackets -->
  <g stroke="#1a73e8" stroke-width="1.8" fill="none" opacity=".42">
    <path d="M18 8L8 8L8 18"/>  <path d="M282 8L292 8L292 18"/>
    <path d="M18 292L8 292L8 282"/> <path d="M282 292L292 292L292 282"/>
  </g>
</svg>`;

  /* ── CSS injected once ─────────────────────────────────────── */
  const CSS = `
/* ── ARIA Avatar wrapper ── */
#iv-avatar-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* spinning conic ring */
.aria-ring-outer {
  position: absolute;
  inset: -7px;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    #1a73e8 0%, #0d47a1 22%, #081e50 38%,
    #1a73e8 52%, #4fc3f7 68%, #1a73e8 100%
  );
  padding: 3px;
  animation: ariaSpinRing 5.5s linear infinite;
  z-index: 0;
}
.aria-ring-outer-in {
  width: 100%; height: 100%;
  border-radius: 50%;
  background: #060a16;
}

/* pulse ring — shown during speaking */
.aria-pulse-ring {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px solid rgba(26,115,232,.45);
  display: none;
  animation: ariaPulse 1.3s ease-in-out infinite;
  z-index: 1;
}
.aria-pulse-ring.show { display: block; }

/* SVG circle */
.aria-svg-circle {
  border-radius: 50%;
  overflow: hidden;
  position: relative;
  z-index: 2;
  box-shadow:
    0 16px 56px rgba(0,0,0,.8),
    inset 0 0 28px rgba(0,0,0,.45);
}

/* ── State animations on the body group ── */
#ariaBodyGroup.idle      { animation: ariaFloat 3.8s ease-in-out infinite; }
#ariaBodyGroup.speaking  { animation: ariaFloat 0.95s ease-in-out infinite; }
#ariaBodyGroup.listening { animation: ariaFloat 3.2s ease-in-out infinite; }
#ariaBodyGroup.thinking  {
  animation: ariaThink 4s cubic-bezier(.4,0,.2,1) infinite;
  transform-origin: 150px 200px;
}

/* eye blink */
#ariaEyeL { animation: ariaEyeBlink 5.5s ease-in-out infinite; transform-origin: 118px 122px; }
#ariaEyeR { animation: ariaEyeBlink 5.5s ease-in-out 0.12s infinite; transform-origin: 182px 122px; }

/* thinking: eyes look up-left + heavy lids */
#ariaBodyGroup.thinking #ariaEyeL {
  animation: ariaThinkLid 4s cubic-bezier(.4,0,.2,1) infinite;
  transform-origin: 118px 122px;
}
#ariaBodyGroup.thinking #ariaEyeR {
  animation: ariaThinkLid 4s cubic-bezier(.4,0,.2,1) infinite 0.06s;
  transform-origin: 182px 122px;
}
#ariaBodyGroup.thinking #ariaIrisL { animation: ariaIrisLook 4s ease-in-out infinite; transform-origin: 118px 122px; }
#ariaBodyGroup.thinking #ariaIrisR { animation: ariaIrisLook 4s ease-in-out infinite; transform-origin: 182px 122px; }

@keyframes ariaSpinRing   { to { transform: rotate(360deg); } }
@keyframes ariaPulse      { 0%,100%{transform:scale(1);opacity:.65} 50%{transform:scale(1.06);opacity:.1} }
@keyframes ariaFloat      { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-9px)} }
@keyframes ariaThink      {
  0%,100% { transform:translateY(0) rotate(0deg) }
  20%,80% { transform:translateY(-7px) rotate(2.5deg) }
  50%     { transform:translateY(-8px) rotate(2.8deg) }
}
@keyframes ariaEyeBlink   { 0%,85%,100%{transform:scaleY(1)} 89%,93%{transform:scaleY(.06)} }
@keyframes ariaThinkLid   {
  0%,100%{transform:scaleY(1)} 15%{transform:scaleY(.5)} 22%{transform:scaleY(.8)}
  45%,65%{transform:scaleY(.75)} 78%{transform:scaleY(.5)} 85%{transform:scaleY(.88)}
}
@keyframes ariaIrisLook   { 0%,100%{transform:translate(0,0)} 25%,75%{transform:translate(-3px,-4px)} }
`;

  /* ── Private state ─────────────────────────────────────────── */
  let _state = 'idle';
  let _mouthTimer = null;
  let _mounted = false;

  /* ── Mount ──────────────────────────────────────────────────── */
  function _mount() {
    console.log('[ARIAAvatar] Attempting mount...');
    // Inject CSS once
    if (!document.getElementById('ariaAvatarStyle')) {
      const style = document.createElement('style');
      style.id = 'ariaAvatarStyle';
      style.textContent = CSS;
      document.head.appendChild(style);
      console.log('[ARIAAvatar] CSS injected.');
    }

    // Support both id conventions
    const container = document.getElementById('iv-avatar-container') ||
      document.getElementById('ariaAvatarContainer');
    
    if (!container) {
      console.warn('[ARIAAvatar] No avatar container found in DOM');
      return false;
    }

    // Detect size from container or default to 210 for SkillMind
    const size = parseInt(container.dataset.size) || container.offsetWidth || 210;
    console.log('[ARIAAvatar] Sizing check:', { dataSize: container.dataset.size, offsetWidth: container.offsetWidth, final: size });

    container.innerHTML = `
      <div class="aria-ring-outer" style="width:${size}px;height:${size}px;">
        <div class="aria-ring-outer-in"></div>
      </div>
      <div class="aria-pulse-ring" id="ariaPulseRing" style="width:${size}px;height:${size}px;"></div>
      <div class="aria-svg-circle" style="width:${size}px;height:${size}px;">
        ${SVG_HTML}
      </div>
    `;

    // Set initial state
    _applyState('idle');
    _mounted = true;
    console.log(`[ARIAAvatar] Mounted Successfully ✓ (size=${size}px)`);
    return true;
  }

  /* ── Apply state ────────────────────────────────────────────── */
  function _applyState(state) {
    console.log('[ARIAAvatar] _applyState ->', state);
    const body = document.getElementById('ariaBodyGroup');
    if (!body) {
      console.warn('[ARIAAvatar] ariaBodyGroup not found!');
      return;
    }

    // Use setAttribute for SVG class application
    body.setAttribute('class', state);
    console.log('[ARIAAvatar] Class applied to body:', body.getAttribute('class'));

    const pulse = document.getElementById('ariaPulseRing');
    if (pulse) {
      pulse.className = 'aria-pulse-ring' + (state === 'speaking' ? ' show' : '');
    }
  }

  /* ── Mouth animation ────────────────────────────────────────── */
  function _startMouth() {
    const teeth = document.getElementById('ariaTeeth');
    let open = false;
    _stopMouth();
    _mouthTimer = setInterval(() => {
      open = !open;
      if (teeth) teeth.setAttribute('opacity', open ? '.88' : '0');
    }, 185);
  }

  function _stopMouth() {
    clearInterval(_mouthTimer);
    _mouthTimer = null;
    const teeth = document.getElementById('ariaTeeth');
    if (teeth) teeth.setAttribute('opacity', '0');
  }

  /* ── Public API ─────────────────────────────────────────────── */
  return {

    mount() {
      return _mount();
    },

    setState(state) {
      console.log('[ARIAAvatar] setState ->', state);
      _state = state;
      _applyState(state);
      if (state !== 'speaking') _stopMouth();
    },

    startMouth() {
      _startMouth();
    },

    stopMouth() {
      _stopMouth();
    },

    getState() {
      return _state;
    },

    isMounted() {
      return _mounted;
    },

    // Legacy shim — old code called avatar.speak() / avatar.stopSpeak()
    speak(text) {
      _applyState('speaking');
      _startMouth();
    },

    stopSpeak() {
      _stopMouth();
      _applyState('idle');
    }
  };

})();

/* ── Auto-mount on DOMContentLoaded ─────────────────────────── */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => ARIAAvatar.mount());
} else {
  ARIAAvatar.mount();  // DOM already ready
}

// Also expose as window.AIAvatarInterviewer shim so existing interview.js code still works
window.AIAvatarInterviewer = null; // signal to interview.js not to re-init
window.ARIAAvatar = ARIAAvatar;
