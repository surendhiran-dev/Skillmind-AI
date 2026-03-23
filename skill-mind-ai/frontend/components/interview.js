/**
 * Skill Mind AI – Interview Module (Vanilla JS)
 * Replaces the React hr-interview Vite app.
 * Self-contained: no dependencies beyond face-api.js (loaded from CDN).
 */
const Interview = (() => {
  'use strict';

  // ── Config ──────────────────────────────────────────
  const API = 'http://127.0.0.1:5000/api';
  // jsDelivr npm CDN — globally cached, much faster than vladmandic GitHub Pages
  const MODELS_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1/model';

  const EMOTION_MAP = {
    neutral:   { e: '😐', label: 'Neutral',   color: '#94a3b8' },
    happy:     { e: '😊', label: 'Happy',      color: '#22c55e' },
    surprised: { e: '😲', label: 'Surprised',  color: '#f59e0b' },
    sad:       { e: '😢', label: 'Sad',        color: '#60a5fa' },
    angry:     { e: '😠', label: 'Angry',      color: '#ef4444' },
    fearful:   { e: '😟', label: 'Nervous',    color: '#f97316' },
    disgusted: { e: '😤', label: 'Disgusted',  color: '#a78bfa' },
  };

  // ── Profanity Filter ────────────────────────────────
  const BAD_WORDS = ['fuck', 'shit', 'damn', 'bitch', 'asshole', 'bastard', 'crap', 'hell', 'piss', 'dick'];

  function filterProfanity(text) {
    if (!text) return '';
    let filtered = text;
    BAD_WORDS.forEach(word => {
      // Precise word boundary matching to avoid masking "classic" as "cl***ic"
      const reg = new RegExp(`\\b${word}\\b`, 'gi');
      filtered = filtered.replace(reg, '*'.repeat(word.length));
    });
    return filtered;
  }

  // ── State ────────────────────────────────────────────
  let token = '';
  let userId = '';
  let sessionToken = '';
  let sessionId = null;
  let questionNumber = 0;
  let currentQuestion = null;
  let stream = null;
  let isJoined = false;
  let isMicOn = true;
  let isCamOn = true;
  let isListening = false;
  let ariaState = 'idle'; // idle | speaking | thinking | listening
  let voiceState = 'idle'; // idle | active | processing | aria-speaking
  let emotionData = EMOTION_MAP.neutral;
  let personCount = 0;
  let strikeCount = 0;
  let noFaceFrames = 0;
  let violationTimer = 0;
  let cooldownActive = false;
  let isTerminated = false;
  let showViolationModal = false;
  let time = 0;
  let timeInterval = null;
  let confidenceScore = 85;
  let finalTextRef = '';
  let interimTextRef = '';
  
  // Advanced Proctoring State
  let baselineDescriptor = null;
  let lipDistanceHistory = [];
  let eyeContactHistory = [];
  let audioContext = null;
  let analyser = null;
  let audioStream = null;
  let faceEngineReady = false;
  let recognition = null;
  let faceInterval = null;
  let answerText = '';
  let avatar = null;

  // ── DOM helpers ──────────────────────────────────────
  const el = id => document.getElementById(id);
  const show = (id, flex=true) => { const e = el(id); if (e) { e.classList.remove('hidden'); e.style.display = flex ? 'flex' : 'block'; } };
  const hide = id => { const e = el(id); if (e) { e.classList.add('hidden'); e.style.display = 'none'; } };
  const html = (id, v) => { const e = el(id); if (e) e.innerHTML = v; };
  const text = (id, v) => { const e = el(id); if (e) e.textContent = v; };

  // ── Auth header ──────────────────────────────────────
  function authHeader() {
    return token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
  }

  // ── API calls ────────────────────────────────────────
  async function apiStartInterview(uid) {
    const res = await fetch(`${API}/interview/start`, {
      method: 'POST',
      headers: authHeader(),
      body: JSON.stringify({ user_id: uid })
    });
    if (!res.ok) throw new Error((await res.json()).error || 'Start failed');
    return res.json();
  }

  async function apiSubmitAnswer(sToken, answer, questionText) {
    const res = await fetch(`${API}/interview/answer`, {
      method: 'POST',
      headers: authHeader(),
      body: JSON.stringify({ token: sToken, answer, question_text: questionText })
    });
    if (!res.ok) throw new Error((await res.json()).error || 'Submit failed');
    return res.json();
  }

  async function apiGetReport(sid) {
    const res = await fetch(`${API}/interview/report/${sid}`, {
      headers: authHeader()
    });
    if (!res.ok) throw new Error((await res.json()).error || 'Report failed');
    return res.json();
  }

  async function apiGetStats() {
    const res = await fetch(`${API}/dashboard/stats`, {
      headers: authHeader()
    });
    if (!res.ok) return null;
    return res.json();
  }

  // ── TTS ──────────────────────────────────────────────
  function speakText(txt) {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(txt);
    utt.rate = 0.95; utt.pitch = 1.05;
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.name.includes('Female') || v.name.includes('Google UK English Female')) || voices[0];
    if (voice) utt.voice = voice;
    utt.onstart = () => {
      setAriaState('speaking');
      if (window.ARIAAvatar) { window.ARIAAvatar.setState('speaking'); window.ARIAAvatar.startMouth(); }
    };
    utt.onend = () => {
      setAriaState('listening');
      if (window.ARIAAvatar) { window.ARIAAvatar.stopMouth(); window.ARIAAvatar.setState('listening'); }
      startSTT();
    };
    utt.onerror = () => {
      if (window.ARIAAvatar) { window.ARIAAvatar.stopMouth(); window.ARIAAvatar.setState('idle'); }
    };
    window.speechSynthesis.speak(utt);
  }

  // ── Avatar / ARIA state ──────────────────────────────
  function setAriaState(state) {
    ariaState = state;
    const statusDot = el('iv-aria-status-dot');
    const statusLbl = el('iv-aria-status-label');
    const stateColors = { speaking: '#22c55e', thinking: '#f59e0b', idle: '#1a73e8', listening: '#1a73e8' };
    const stateLabels = { speaking: 'Speaking', thinking: 'Thinking', idle: 'Ready', listening: 'Listening' };
    if (statusDot) statusDot.style.background = stateColors[state] || '#1a73e8';
    if (statusLbl) { statusLbl.textContent = stateLabels[state] || state; statusLbl.style.color = stateColors[state] || '#1a73e8'; }
    updateTeethAnimation(state === 'speaking');

    // Drive voice UI based on ARIA state
    if (state === 'speaking' || state === 'thinking') {
      setVoiceState('aria-speaking');
    } else if (state === 'listening') {
      // Only reset to idle if we were in aria-speaking (i.e., mic not actively recording)
      if (voiceState === 'aria-speaking') {
        setVoiceState('idle');
      }
    }
  }

  function updateTeethAnimation(speaking) {
    if (!speaking) return;
    let teeth = el('ariaTeeth');
    if (teeth) {
      let tog = false;
      const iv = setInterval(() => {
        if (ariaState !== 'speaking') { clearInterval(iv); teeth.style.opacity = 0; return; }
        tog = !tog; teeth.style.opacity = tog ? 0.84 : 0;
      }, 150);
    }
  }

  // ────────────────────────────────────────────────────
  //  VOICE STATE MACHINE
  //  States: idle | active | processing | aria-speaking
  // ────────────────────────────────────────────────────
  function setVoiceState(state) {
    voiceState = state;

    const tapBtn    = el('iv-tap-mic-btn');
    const tapLabel  = el('iv-tap-mic-label');
    const tapIcon   = el('iv-tap-mic-icon');
    const finishBtn = el('iv-finish-btn');
    const finishLbl = el('iv-finish-label');
    const finishIco = el('iv-finish-icon');
    const spinner   = el('iv-finish-spinner');
    const micStatus = el('iv-mic-status');
    const micStatusTxt = el('iv-mic-status-text');
    const audioWave = el('iv-audio-wave');
    const placeholder = el('iv-sub-placeholder');

    switch (state) {

      case 'active':
        // STOP: red pulsing, active label
        if (tapBtn) {
          tapBtn.disabled = false;
          tapBtn.classList.add('mic-active');
          tapBtn.style.opacity = '';
        }
        if (tapLabel) tapLabel.textContent = 'STOP';
        if (tapIcon)  tapIcon.innerHTML  = '<i class="fas fa-stop-circle"></i>';

        // FINISH ANSWER: hidden while recording to prevent premature clicks
        if (finishBtn) {
          finishBtn.style.display = 'none';
        }

        // Show overlays
        if (micStatus) { micStatus.style.display = 'flex'; }
        if (micStatusTxt) micStatusTxt.textContent = '🎤 ARIA Listening...';
        if (audioWave) audioWave.style.display = 'flex';

        // Hide placeholder
        if (placeholder) placeholder.style.display = 'none';
        break;

      case 'idle':
        // TAP TO START: blue, enabled, normal label
        if (tapBtn) {
          tapBtn.disabled = false;
          tapBtn.classList.remove('mic-active');
          tapBtn.style.opacity = '';
        }
        if (tapLabel) tapLabel.textContent = 'TAP TO START';
        if (tapIcon)  tapIcon.textContent  = '🎤';

        // FINISH ANSWER: Show only if there's content to submit
        const hasText = !!(answerText.trim() || finalTextRef.trim());
        if (finishBtn) {
           finishBtn.style.display = hasText ? 'flex' : 'none';
           finishBtn.disabled = false;
        }
        if (finishLbl) finishLbl.textContent = 'FINISH ANSWER';
        if (finishIco) finishIco.innerHTML = '<i class="fas fa-check-circle"></i>';
        if (spinner)   spinner.style.display = 'none';

        // Overlays: hidden
        if (micStatus) micStatus.style.display = 'none';
        if (audioWave) audioWave.style.display = 'none';

        // Subtitle placeholder
        if (placeholder) placeholder.style.display = hasText ? 'none' : '';
        break;

      case 'processing':
        // STOP: disabled
        if (tapBtn) {
          tapBtn.disabled = true;
          tapBtn.classList.remove('mic-active');
        }
        if (tapLabel) tapLabel.textContent = 'STOP';
        if (tapIcon)  tapIcon.textContent  = '🎤';

        // FINISH ANSWER: visible but disabled with spinner
        if (finishBtn) {
          finishBtn.style.display = 'flex';
          finishBtn.disabled = true;
        }
        if (finishLbl) finishLbl.textContent = 'SENDING...';
        if (finishIco) finishIco.textContent = '';
        if (spinner)   spinner.style.display = 'inline-block';

        // Show Processing... status
        if (micStatus) { micStatus.style.display = 'flex'; }
        if (micStatusTxt) micStatusTxt.textContent = '⏳ ARIA Processing...';
        if (audioWave) audioWave.style.display = 'none';
        break;

      case 'aria-speaking':
        // TAP TO START: disabled grey
        if (tapBtn) {
          tapBtn.disabled = true;
          tapBtn.classList.remove('mic-active');
        }
        if (tapLabel) tapLabel.textContent = 'TAP TO START';
        if (tapIcon)  tapIcon.textContent  = '🎤';

        // FINISH ANSWER: hidden
        if (finishBtn) finishBtn.style.display = 'none';
        if (spinner)   spinner.style.display   = 'none';

        // All overlays hidden
        if (micStatus) micStatus.style.display = 'none';
        if (audioWave) audioWave.style.display = 'none';

        // Reset subtitle to awaiting
        resetSubtitle();
        break;
    }

    // Always sync the legacy audio dot
    updateMicUI();
  }

  // ── Face detection ───────────────────────────────────
  async function initFaceEngine() {
    try {
      if (!window.faceapi) throw new Error('face-api.js not loaded');
      await Promise.all([
        window.faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_URL),
        window.faceapi.nets.faceExpressionNet.loadFromUri(MODELS_URL),
        window.faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL),
        window.faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL)
      ]);
      faceEngineReady = true;
      console.log('[FaceEngine] Advanced Mode Ready ✓');
    } catch (e) {
      console.error('[FaceEngine] Init Error:', e);
    }
  }

  function startFaceLoop() {
    const video = el('iv-video');
    const canvas = el('iv-canvas');
    if (!video || !canvas) return;
    faceInterval = setInterval(async () => {
      if (!faceEngineReady || !video || video.paused || video.videoWidth === 0) return;
      try {
        const opts = new window.faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.4 });
        const detections = await window.faceapi.detectAllFaces(video, opts).withFaceExpressions();
        const dw = video.offsetWidth, dh = video.offsetHeight;
        canvas.width = dw; canvas.height = dh;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, dw, dh);
        const count = detections.length;
        personCount = count;
        text('iv-person-count', count);
        if (count === 1) {
          noFaceFrames = 0; 
          hideEl('iv-no-face-warning'); 
          hideEl('iv-multi-person-warning');
          violationTimer = 0;
          el('iv-person-badge') && (el('iv-person-badge').style.display = 'flex');
        } else {
          // 0 or >1 persons = violation
          if (count === 0) {
            noFaceFrames++;
            if (noFaceFrames >= 3) showEl('iv-no-face-warning');
            hideEl('iv-multi-person-warning');
          } else {
            noFaceFrames = 0; 
            hideEl('iv-no-face-warning');
            showEl('iv-multi-person-warning');
            el('iv-multi-person-count') && (el('iv-multi-person-count').textContent = count);
          }

          el('iv-person-badge') && (el('iv-person-badge').style.display = 'none');

          if (!cooldownActive && !showViolationModal && !isTerminated) {
            violationTimer += 0.75; // Match interval (750ms)
            if (violationTimer >= 1.5) { // ~2 frames of violation
              violationTimer = 0;
              strikeCount++;
              text('iv-strike-count', strikeCount);
              updateStrikeDots();
              if (strikeCount >= 3) {
                isTerminated = true;
                window.speechSynthesis && window.speechSynthesis.cancel();
                recognition && recognition.stop();
                showViolationModalFn(true, count === 0);
              } else {
                window.speechSynthesis && window.speechSynthesis.cancel();
                recognition && recognition.stop();
                showViolationModalFn(false, count === 0);
              }
            }
          }
        }
        // Draw bounding boxes
        const scaleX = dw / video.videoWidth, scaleY = dh / video.videoHeight;
        detections.forEach((det, idx) => {
          const box = det.detection.box;
          const x = box.x * scaleX, y = box.y * scaleY, w = box.width * scaleX, h = box.height * scaleY;
          ctx.strokeStyle = idx === 0 ? '#22c55e' : '#ef4444';
          ctx.lineWidth = 2;
          ctx.strokeRect(x, y, w, h);
          if (idx === 0 && det.expressions) {
            let topKey = 'neutral', topVal = 0;
            Object.entries(det.expressions).forEach(([k, v]) => { if (v > topVal) { topVal = v; topKey = k; } });
            emotionData = EMOTION_MAP[topKey] || EMOTION_MAP.neutral;
            updateEmotionBadge();
          }
        });
      } catch (e) { /* ignore frame errors */ }
    }, 750); // 750ms — 1.5s detection (2 frames)
  }

  function updateEmotionBadge() {
    const badge = el('iv-emotion-badge');
    if (badge) badge.innerHTML = `<span>${emotionData.e}</span><span class="iv-emotion-label">${emotionData.label}</span>`;
    const faceReactionEl = el('iv-metric-emotion');
    if (faceReactionEl) faceReactionEl.textContent = `${emotionData.e} ${emotionData.label}`;
  }

  function showEl(id) { const e = el(id); if (e) e.style.display = ''; }
  function hideEl(id) { const e = el(id); if (e) e.style.display = 'none'; }

  // ── Strike dots ──────────────────────────────────────
  function updateStrikeDots() {
    [1, 2, 3].forEach(s => {
      const dot = el(`iv-strike-dot-${s}`);
      if (dot) dot.classList.toggle('iv-strike-dot-hit', s <= strikeCount);
    });
  }

  // ── Violation modal ──────────────────────────────────
  function showViolationModalFn(terminated, isNoFace) {
    showViolationModal = true;
    const modal = el('iv-violation-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    const title = el('iv-violation-title');
    const msg = el('iv-violation-msg');
    const icon = el('iv-violation-icon');
    const btn = el('iv-violation-btn');

    if (terminated) {
      if (icon) icon.textContent = '🛑';
      if (title) title.textContent = 'Interview Terminated';
      const reasonLabel = isNoFace ? 'Proctoring Violation: Face Not Detected' : 'Security Violation: Multiple Faces Detected';
      if (msg) msg.innerHTML = `You have received <strong>3 security violations</strong>.<br><br><strong style="color:#ef4444">${reasonLabel}</strong><br><br><strong style="color:#ef4444">Your interview has been permanently terminated.</strong>`;
      if (btn) { 
        btn.textContent = '📋 View Partial Report'; 
        btn.onclick = async () => {
          try {
            btn.disabled = true;
            btn.textContent = 'Loading Report...';
            const data = await apiGetReport(sessionId);
            hide('iv-violation-modal');
            showReport(data);
          } catch(e) {
            showError('Failed to load partial report.');
            btn.disabled = false;
            btn.textContent = '📋 View Partial Report';
          }
        };
      }
    } else {
      if (icon) icon.textContent = strikeCount === 2 ? '⛔' : '🚨';
      if (title) title.textContent = `Strike ${strikeCount} — Security Alert!`;
      const reasonLabel = isNoFace ? 'Proctoring Violation: Face Not Detected' : 'Security Violation: Multiple Faces Detected';
      const action = isNoFace ? 'Please ensure your face is clearly visible and centered on the camera.' : 'Please remove any additional persons from the frame immediately.';
      if (msg) msg.innerHTML = `<strong style="color:#fbbf24">${reasonLabel}</strong><br>This violates interview integrity rules.<br><br>${action}<br><br><strong style="color:#fbbf24">⚠️ ${3 - strikeCount} more violation${3 - strikeCount > 1 ? 's' : ''} will permanently end your interview.</strong>`;
      if (btn) { btn.textContent = 'I Understand'; btn.onclick = dismissViolation; }
    }
    updateStrikeDots();
  }

  function dismissViolation() {
    showViolationModal = false;
    const modal = el('iv-violation-modal');
    if (modal) modal.style.display = 'none';
    cooldownActive = true;
    violationTimer = 0;
    setTimeout(() => { cooldownActive = false; }, 8000);
    if (ariaState === 'listening') startSTT();
  }

  // ── STT ── ──────────────────────────────────────────
  function initSTT() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    recognition = new SR();
    recognition.continuous      = true;
    recognition.interimResults  = true;
    recognition.lang            = 'en-US';
    recognition.maxAlternatives = 1; // Faster locking on results

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const best = result[0]; // Trust primary result for speed
        if (result.isFinal) {
          const chunk = filterProfanity(best.transcript.trim());
          if (chunk) finalTextRef = finalTextRef ? finalTextRef + ' ' + chunk : chunk;
          interimTextRef = '';
        } else {
          interimTextRef = filterProfanity(best.transcript);
        }
      }
      answerText = finalTextRef + (interimTextRef ? ' ' + interimTextRef.trim() : '');
      updateSubtitleLive(finalTextRef, interimTextRef);
    };

    recognition.onend = () => {
      // Aggressive auto-restart for better reliability
      if (isListening && isMicOn && ariaState === 'listening' && !isTerminated) {
        try { recognition.start(); } catch(e) {}
      } else {
        isListening = false;
        if (voiceState === 'active') setVoiceState('idle');
        updateMicUI();
      }
    };

    recognition.onerror = (event) => {
      if (event.error === 'aborted' || event.error === 'no-speech') return;
      console.warn('[STT] Error:', event.error);
      if (isListening && ariaState === 'listening' && !isTerminated) {
        // Shorter timeout for faster recovery
        setTimeout(() => { try { recognition.start(); } catch(e) {} }, 100);
      }
    };
  }

  function startSTT() {
    if (!recognition || isTerminated) return;
    if (isListening) return;
    try {
      recognition.start();
      isListening = true;
      setVoiceState('active');
      updateMicUI();
    } catch(e) {
      console.warn('[STT] Start error:', e);
    }
  }

  function stopSTT() {
    if (!recognition) return;
    isListening = false;
    try { recognition.stop(); } catch(e) {}
    updateMicUI();
  }

  function updateMicUI() {
    const dot = el('iv-audio-dot');
    const lbl = el('iv-audio-label');
    if (dot) dot.className = `iv-metric-dot ${isListening ? 'iv-dot-green' : 'iv-dot-dim'}`;
    if (lbl) lbl.textContent = isListening ? 'LIVE' : 'OFF';
  }

  // ── Subtitle helpers ─────────────────────────────────

  /**
   * Update the live ANS subtitle with separate final (white) and interim (grey italic) spans.
   */
  function updateSubtitleLive(finalText, interimText) {
    const subFinal   = el('iv-sub-final');
    const subInterim = el('iv-sub-interim');
    const placeholder = el('iv-sub-placeholder');

    if (subFinal)   subFinal.textContent   = finalText || '';
    if (subInterim) subInterim.textContent = interimText ? ' ' + interimText : '';

    // Show/hide placeholder
    const hasContent = !!(finalText || interimText);
    if (placeholder) placeholder.style.display = hasContent ? 'none' : '';

    // Also sync the textarea
    const inp = el('iv-answer-input');
    if (inp) inp.value = finalText + (interimText ? ' ' + interimText : '');
  }

  function resetSubtitle() {
    finalTextRef   = '';
    interimTextRef = '';
    answerText     = '';
    updateSubtitleLive('', '');
    const inp = el('iv-answer-input');
    if (inp) inp.value = '';
  }

  function updateAnswerDisplay() {
    // Legacy function — used by textarea input handler
    updateSubtitleLive(finalTextRef, interimTextRef);
  }

  // ── Timer ────────────────────────────────────────────
  function startTimer() {
    timeInterval = setInterval(() => {
      time++;
      const m = Math.floor(time / 60), s = time % 60;
      text('iv-timer', `${m}:${s.toString().padStart(2, '0')}`);
    }, 1000);
  }

  function startNextQuestionCountdown(nextQ) {
    if (!nextQ) return;
    const modal = el('iv-countdown-modal');
    const numEl = el('iv-countdown-num');
    const circle = el('iv-countdown-circle');
    if (!modal || !numEl) {
      // Fallback if modal missing
      displayQuestion(nextQ);
      return;
    }

    modal.style.display = 'flex';
    modal.classList.remove('hidden');
    let count = 5;
    numEl.textContent = count;
    if (circle) circle.style.strokeDashoffset = '0';

    const cdInt = setInterval(() => {
      count--;
      numEl.textContent = count;
      if (circle) {
        // SVG circle dasharray is ~283 for r=45
        const offset = 283 - (283 * (count / 5));
        circle.style.strokeDashoffset = offset;
      }
      
      if (count <= 0) {
        clearInterval(cdInt);
        modal.style.display = 'none';
        displayQuestion(nextQ);
      }
    }, 1000);
  }

  // ── Question progress dots ────────────────────────────
  function updateProgress() {
    const wrapper = el('iv-progress-dots');
    const label = el('iv-question-label');
    if (!wrapper) return;
    wrapper.innerHTML = Array.from({ length: 6 }, (_, i) => {
      const n = i + 1;
      const cls = n < questionNumber ? 'iv-dot iv-dot-done' : n === questionNumber ? 'iv-dot iv-dot-active' : 'iv-dot iv-dot-dim';
      return `<div class="${cls}"></div>`;
    }).join('');
    if (label) label.textContent = `Question ${questionNumber}/6`;
  }

  // ── Question display ──────────────────────────────────
  function displayQuestion(q) {
    currentQuestion = q;
    const fullText = (q.acknowledgment ? q.acknowledgment + ' ' : '') + q.question;
    const ariaSub = el('iv-aria-subtitle');
    if (ariaSub) { ariaSub.style.display = 'flex'; ariaSub.querySelector('.iv-subtitle-text').textContent = fullText; }
    speakText(fullText);
    updateProgress();
  }

  // ── Tap Mic button handler ────────────────────────────
  function handleTapMic() {
    if (isTerminated) return;
    if (voiceState === 'active') {
      // Stop recording — just reset to idle, don't auto-send
      stopSTT();
      setVoiceState('idle');
    } else if (voiceState === 'idle') {
      // Start recording
      finalTextRef   = '';
      interimTextRef = '';
      answerText     = '';
      updateSubtitleLive('', '');
      startSTT();
    }
  }

  // ── Handle answer submit ──────────────────────────────
  async function handleSend() {
    // Collect from voice + any typed text
    const inp = el('iv-answer-input');
    if (inp && inp.value.trim() && !answerText.trim()) {
      answerText = inp.value.trim();
      finalTextRef = answerText;
    }
    const answer = (finalTextRef + ' ' + interimTextRef).trim() || answerText.trim();
    if (!answer || ariaState === 'thinking' || isTerminated) return;
    if (personCount > 1) {
      showError('Submission blocked: Multiple persons detected.'); return;
    }

    // Stop mic and show processing state
    stopSTT();
    setVoiceState('processing');

    const savedAnswer = answer;
    // Clear for next round
    finalTextRef   = '';
    interimTextRef = '';
    answerText     = '';
    updateSubtitleLive('', '');
    if (inp) inp.value = '';

    setAriaState('thinking');
    if (window.ARIAAvatar) window.ARIAAvatar.setState('thinking');

    try {
      const data = await apiSubmitAnswer(sessionToken, savedAnswer, currentQuestion?.question || '');
      if (data.evaluation?.answer_score) {
        confidenceScore = data.evaluation.answer_score;
        const confEl = el('iv-confidence-score');
        if (confEl) confEl.textContent = `${confidenceScore}%`;
        const confBar = el('iv-confidence-bar');
        if (confBar) confBar.style.width = `${confidenceScore}%`;
      }
      if (data.status === 'complete') {
        clearInterval(timeInterval);
        clearInterval(faceInterval);
        recognition && recognition.stop();
        window.speechSynthesis && window.speechSynthesis.cancel();
        showReport(data.report || {});
      } else {
        questionNumber = data.question_number;
        // Start 5s countdown instead of immediate question
        const nextQ = data.next_question || data.response;
        if (nextQ) {
          startNextQuestionCountdown(nextQ);
        } else {
          // If no content, just skip to default (though shouldn't happen)
          displayQuestion('Thinking...');
        }
      }
      clearError();
    } catch (e) {
      setAriaState('listening');
      if (window.ARIAAvatar) window.ARIAAvatar.setState('listening');
      setVoiceState('idle');
      showError(`Submission failed: ${e.message}`);
    }
  }

  function showError(msg) { const e = el('iv-error-msg'); if (e) { e.textContent = msg; e.style.display = 'block'; } }
  function clearError() { const e = el('iv-error-msg'); if (e) e.style.display = 'none'; }

  // ── Pre-join screen ──────────────────────────────────
  async function showPreJoin() {
    hide('iv-room'); hide('iv-report');
    show('iv-prejoin');
    try {
      const stats = await apiGetStats();
      if (stats?.report) {
        const r = stats.report;
        setStatCard('iv-stat-resume', r.resume_strength || 0);
        setStatCard('iv-stat-quiz', r.quiz_score || 0);
        setStatCard('iv-stat-coding', r.coding_score || 0);
        setStatCard('iv-stat-interview', r.interview_score || 0);
      }
      if (stats?.skills?.length) {
        const skillsEl = el('iv-skills-display');
        if (skillsEl) skillsEl.innerHTML = stats.skills.map(s => `<span class="iv-skill-tag">${s}</span>`).join('');
      }
    } catch(e) { console.warn('Stats load failed:', e); }
    hide('iv-prejoin-loading');
    show('iv-prejoin-content', true); // Uses flex from CSS
  }

  function setStatCard(id, val) { 
    const e = el(id); 
    if (e) {
      // Round to 1 decimal place if it's a number
      const num = typeof val === 'number' ? val : parseFloat(val);
      const rounded = isNaN(num) ? val : Math.round(num * 10) / 10;
      e.textContent = `${rounded}${typeof rounded === 'number' ? '%' : ''}`; 
    }
  }

  // ── Join interview ────────────────────────────────────
  async function handleJoin() {
    const btn = el('iv-join-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Preparing Session...'; }
    try {
      const data = await apiStartInterview(userId);
      sessionToken = data.token;
      sessionId = data.session_id;
      questionNumber = 1;

      // Camera Enrollment
      try {
        stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 1280, height: 720 }, 
          audio: true 
        });
        
        // Confirm we have a video track
        const videoTrack = stream.getVideoTracks()[0];
        if (!videoTrack) throw new Error('No video track found');

        const vid = el('iv-video');
        if (vid) { 
          vid.srcObject = stream; 
          vid.play().catch(()=>{}); 
        }
        isCamOn = true;
        isMicOn = true;
      } catch(e) {
        console.error('[Camera] Access failed:', e);
        showError('Please turn on your camera to start the interview. Camera access is required for proctoring.');
        if (btn) { btn.disabled = false; btn.textContent = 'Join Interview Now'; }
        return; // STOP HERE
      }

      isJoined = true;
      hide('iv-prejoin'); show('iv-room'); hide('iv-report');
      startFaceLoop();
      startTimer();
      initSTT();
      displayQuestion(data.response);
    } catch(e) {
      showError(`Could not start interview: ${e.message}`);
      if (btn) { btn.disabled = false; btn.textContent = 'Join Interview Now'; }
    }
  }

  // ── Report screen ─────────────────────────────────────
  function showReport(report) {
    hide('iv-room'); hide('iv-prejoin');
    show('iv-report');
    const score = Math.round(report.hr_interview_score || 0);
    const readiness = report.readiness_level || 'Moderate';
    const summary = report.ai_summary || '';
    const strengths = report.top_strengths ? report.top_strengths.split(',') : [];
    const areas = report.improvement_areas ? report.improvement_areas.split(',') : [];
    const recommendation = report.recommendation || '';

    text('iv-rep-score', `${score}%`);
    text('iv-rep-readiness', readiness);
    text('iv-rep-summary', summary);
    text('iv-rep-behavioral', report.behavioral_rating || 0);
    text('iv-rep-communication', report.communication_rating || 0);
    text('iv-rep-technical', report.technical_rating || 0);
    text('iv-rep-confidence', report.confidence_index || 0);
    animateBars(report);

    const strEl = el('iv-rep-strengths');
    if (strEl) strEl.innerHTML = strengths.map(s => `<span class="iv-strength-tag">${s.trim()}</span>`).join('');
    const recEl = el('iv-rep-recommendation');
    if (recEl) recEl.textContent = recommendation;

    // Animate score circle
    const circle = el('iv-rep-circle');
    if (circle) {
      const val = 440 - (440 * score / 100);
      circle.style.transition = 'stroke-dashoffset 2s ease';
      circle.style.strokeDashoffset = val;
    }

    // Load detailed QA log
    if (sessionId) {
      apiGetReport(sessionId).then(data => {
        if (data?.qa_log) renderQALog(data.qa_log);
      }).catch(() => {});
    }
  }

  function animateBars(report) {
    const dims = [
      ['iv-bar-behavioral', report.behavioral_rating],
      ['iv-bar-communication', report.communication_rating],
      ['iv-bar-technical', report.technical_rating],
      ['iv-bar-confidence', report.confidence_index],
    ];
    dims.forEach(([id, val]) => {
      const bar = el(id);
      if (bar) setTimeout(() => { bar.style.width = `${(val || 0) * 10}%`; }, 400);
    });
  }

  function renderQALog(qaLog) {
    const container = el('iv-qa-log');
    if (!container) return;
    container.innerHTML = qaLog.map((qa, i) => `
      <div class="iv-qa-item">
        <div class="iv-qa-header">
          <span class="iv-qa-badge">Q${i + 1}</span>
          <p class="iv-qa-question">${qa.question}</p>
          <span class="iv-qa-score">${qa.score}/100</span>
        </div>
        <div class="iv-qa-answer">"${qa.answer}"</div>
        <p class="iv-qa-feedback">⚡ ${qa.feedback}</p>
      </div>
    `).join('');
  }

  // ── Public Init ──────────────────────────────────────
  async function init(jwtToken, uid) {
    token = jwtToken;
    userId = uid;

    // Reset all state
    sessionToken = ''; sessionId = null; questionNumber = 0; currentQuestion = null;
    stream = null; isJoined = false; isMicOn = true; isCamOn = true;
    isListening = false; ariaState = 'idle'; voiceState = 'idle'; time = 0;
    strikeCount = 0; noFaceFrames = 0; violationTimer = 0;
    cooldownActive = false; isTerminated = false; showViolationModal = false;
    confidenceScore = 85; finalTextRef = ''; interimTextRef = ''; answerText = '';
    baselineDescriptor = null; lipDistanceHistory = []; eyeContactHistory = [];
    if (audioContext) { audioContext.close(); audioContext = null; }
    clearInterval(timeInterval); clearInterval(faceInterval);

    // DOM bindings
    const joinBtn = el('iv-join-btn');
    if (joinBtn) joinBtn.onclick = handleJoin;

    // Legacy send button (hidden, kept for compatibility)
    const sendBtn = el('iv-send-btn');
    if (sendBtn) sendBtn.onclick = handleSend;

    // New FINISH ANSWER button
    const finishBtn = el('iv-finish-btn');
    if (finishBtn) finishBtn.onclick = handleSend;

    // New STOP / START button
    const tapMicBtn = el('iv-tap-mic-btn');
    if (tapMicBtn) tapMicBtn.onclick = handleTapMic;

    // Textarea: sync typed text into transcript refs
    const ansInput = el('iv-answer-input');
    if (ansInput) {
      ansInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
      });
      ansInput.addEventListener('input', e => {
        const val = filterProfanity(e.target.value);
        e.target.value = val; // Force filtered value back into textarea
        finalTextRef = val;
        interimTextRef = '';
        answerText = val;
        // Show FINISH ANSWER when user types
        const fBtn = el('iv-finish-btn');
        if (fBtn && val.trim() && voiceState === 'idle') {
          fBtn.style.display = 'flex';
          fBtn.disabled = false;
        } else if (fBtn && !val.trim() && voiceState === 'idle') {
          fBtn.style.display = 'none';
        }
        updateSubtitleLive(finalTextRef, '');
      });
    }

    // Mic stream toggle button (existing small mic 🎙 in controls area)
    const micBtn = el('iv-mic-btn');
    if (micBtn) micBtn.onclick = () => {
      isMicOn = !isMicOn;
      if (stream) stream.getAudioTracks().forEach(t => t.enabled = isMicOn);
      micBtn.classList.toggle('iv-btn-active', isMicOn);
      micBtn.classList.toggle('iv-btn-danger', !isMicOn);
      if (!isMicOn) stopSTT(); else if (isJoined && ariaState === 'listening') startSTT();
    };

    const camBtn = el('iv-cam-btn');
    if (camBtn) camBtn.onclick = () => {
      isCamOn = !isCamOn;
      if (stream) stream.getVideoTracks().forEach(t => t.enabled = isCamOn);
      const vid = el('iv-video');
      if (vid) vid.style.display = isCamOn ? 'block' : 'none';
      camBtn.classList.toggle('iv-btn-active', isCamOn);
      camBtn.classList.toggle('iv-btn-danger', !isCamOn);
    };

    const endBtn = el('iv-end-btn');
    if (endBtn) endBtn.onclick = () => show('iv-end-modal');

    const confirmContinue = el('iv-confirm-continue');
    if (confirmContinue) confirmContinue.onclick = () => hide('iv-end-modal');

    const confirmEnd = el('iv-confirm-end');
    if (confirmEnd) confirmEnd.onclick = () => { stream && stream.getTracks().forEach(t => t.stop()); showPreJoin(); };

    const backBtn = el('iv-rep-back-btn');
    if (backBtn) backBtn.onclick = () => { window.location.href = '/'; };

    // Init face engine in background
    initFaceEngine();

    // Init 3D Avatar — use ARIAAvatar SVG (already auto-mounted)
    if (window.ARIAAvatar && !window.ARIAAvatar.isMounted()) {
      window.ARIAAvatar.mount();
    }

    // Show pre-join
    showPreJoin();
  }

  return { init };
})();
