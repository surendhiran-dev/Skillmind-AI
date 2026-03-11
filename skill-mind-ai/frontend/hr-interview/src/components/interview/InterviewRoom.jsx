import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useInterviewEngine } from '../../hooks/useInterviewEngine';
import AriaAvatar from './AriaAvatar';
import TranscriptPanel from './TranscriptPanel';
import axios from 'axios';
import { 
  Mic, MicOff, Video, VideoOff, Send, 
  PhoneOff, Timer, Layout, MessageCircle, 
  Settings, User, Info, MoreVertical, Brain,
  CheckCircle, Zap, BarChart, Code, Target
} from 'lucide-react';

const InterviewRoom = ({ onComplete }) => {
  const {
    transcript,
    currentQuestion,
    sessionId,
    isComplete,
    loading,
    questionNumber,
    startInterview,
    submitAnswer,
    getReport
  } = useInterviewEngine();

  const [isMicOn, setIsMicOn] = useState(true);
  const [isCamOn, setIsCamOn] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [answerInput, setAnswerInput] = useState('');
  const [ariaState, setAriaState] = useState('idle'); // idle, speaking, thinking, listening
  const [time, setTime] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [stream, setStream] = useState(null);
  const [isJoined, setIsJoined] = useState(false);
  const [candidateStats, setCandidateStats] = useState(null);
  const [fetchingStats, setFetchingStats] = useState(true);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const recognitionRef = useRef(null);
  const scrollRef = useRef(null);
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);

  // Colors from Prompt
  const colors = {
    bgDark: '#0d0e14',
    bgCard: '#16171f',
    bgMeet: '#1c1e26',
    accent: '#1a73e8',
    accent2: '#34a853',
    danger: '#ea4335',
    textMain: '#e8eaed',
    textDim: '#9aa0a6'
  };

  // ── Fetch Candidate Stats ──
  useEffect(() => {
    const fetchStats = async () => {
      try {
        let token = sessionStorage.getItem('token');
        if (!token) {
          const params = new URLSearchParams(window.location.search);
          token = params.get('token');
        }

        const { data } = await axios.get('http://127.0.0.1:5000/api/dashboard/stats', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCandidateStats(data);
      } catch (err) {
        console.error('Failed to fetch candidate stats:', err);
      } finally {
        setFetchingStats(false);
      }
    };
    fetchStats();
  }, []);

  // ── Initialize STT ──
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = 'en-US';
      
      rec.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setAnswerInput(transcript);
      };
      
      rec.onerror = () => setIsListening(false);
      rec.onend = () => setIsListening(false);
      recognitionRef.current = rec;
    }
  }, []);

  const toggleSTT = () => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
      setIsListening(true);
    }
  };

  // ── Timer ──
  useEffect(() => {
    let interval;
    if (isJoined && !isComplete) {
      interval = setInterval(() => setTime(t => t + 1), 1000);
    }
    return () => clearInterval(interval);
  }, [isJoined, isComplete]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  // ── Text to Speech (ARIA's Voice) ──
  const speakText = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.05;
    
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.name.includes('Female') || v.name.includes('Google UK English Female')) || voices[0];
    if (voice) utterance.voice = voice;

    utterance.onstart = () => setAriaState('speaking');
    utterance.onend = () => {
      setAriaState('listening');
      // Focus input automatically
    };
    
    window.speechSynthesis.speak(utterance);
  };

  // ── Auto-speak on next question ──
  useEffect(() => {
    if (currentQuestion && isJoined) {
      const fullText = (currentQuestion.acknowledgment ? currentQuestion.acknowledgment + " " : "") + currentQuestion.question;
      speakText(fullText);
    }
  }, [currentQuestion, isJoined]);

  // ── Auto-scroll transcript ──
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, answerInput]);

  // ── Auto-start Mic when ARIA is done ──
  useEffect(() => {
    if (ariaState === 'listening' && recognitionRef.current && !isListening && isMicOn) {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (e) {
        console.error("Auto-mic start failed:", e);
      }
    }
  }, [ariaState, isMicOn]);

  // ── Sync Stream to Video Element ──
  useEffect(() => {
    console.log("Stream Sync Effect:", { isJoined, hasStream: !!stream, hasRef: !!videoRef.current, isCamOn });
    if (isJoined && stream && videoRef.current && isCamOn) {
      if (videoRef.current.srcObject !== stream) {
        console.log("Attaching stream to video element");
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(e => console.error("Video play failed:", e));
      }
    }
  }, [isJoined, stream, isCamOn]);

  // ── Audio Waveform Logic ──
  useEffect(() => {
    if (isJoined && stream && isMicOn && canvasRef.current) {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      audioCtxRef.current = audioCtx;
      analyserRef.current = analyser;

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        animationFrameRef.current = requestAnimationFrame(draw);
        analyser.getByteFrequencyData(dataArray);

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw centered line
        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();

        // Waveform
        ctx.beginPath();
        ctx.lineWidth = 2;
        ctx.strokeStyle = colors.accent;
        ctx.lineCap = 'round';
        
        const sliceWidth = canvas.width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 128.0;
          const y = (v * canvas.height) / 2;

          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
          x += sliceWidth;
        }
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
      };
      draw();

      return () => {
        cancelAnimationFrame(animationFrameRef.current);
        if (audioCtxRef.current) audioCtxRef.current.close();
      };
    }
  }, [isJoined, stream, isMicOn]);

  // ── Join Logic ──
  const handleJoin = async () => {
    try {
      // Storage fallback: Try URL parameters if sessionStorage is blocked or empty
      let userId = sessionStorage.getItem('user_id');
      if (!userId) {
        const params = new URLSearchParams(window.location.search);
        userId = params.get('user_id');
        if (userId) {
          console.log('InterviewRoom: Retrieved user_id from URL fallback');
        }
      }
      
      userId = userId || 1; 
      await startInterview(userId);
      
      // Init Webcam
      try {
        const userStream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 1280, height: 720 }, 
          audio: true 
        });
        setStream(userStream);
      } catch (e) {
        console.warn('Webcam failed:', e);
        setIsCamOn(false);
        setIsMicOn(false);
        if (e.name === 'NotAllowedError') {
          setErrorMessage('Camera/Mic permission denied by System. Please check Windows Privacy Settings or your Antivirus.');
        } else {
          setErrorMessage('Could not access camera/mic. Please ensure no other app is using them.');
        }
      }
      
      setIsJoined(true);
    } catch (err) {
      setErrorMessage('Could not connect to ARIA. Please check server.');
    }
  };

  // ── Submit Logic ──
  const handleSend = async () => {
    if (!answerInput.trim() || loading) return;
    
    const answer = answerInput;
    setAnswerInput('');
    if (isListening) recognitionRef.current.stop();
    
    setAriaState('thinking');
    const result = await submitAnswer(answer, currentQuestion?.question);
    
    if (result?.status === 'complete') {
      const fullReport = await getReport(sessionId);
      onComplete(fullReport);
    }
  };

  // ── Pre-Interview Card ──
  if (!isJoined) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-[#0d0e14] p-4 md:p-6 font-['Plus_Jakarta_Sans']">
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-[#16171f] border border-white/10 rounded-[2.5rem] p-6 md:p-10 max-w-2xl w-full shadow-2xl relative overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center gap-6 mb-10 text-left">
            <div className="relative">
              <div className="w-32 h-32 rounded-full bg-blue-500/10 border-2 border-blue-500/20 p-2">
                <div className="w-full h-full flex items-center justify-center">
                  <AriaAvatar state="idle" size={120} hideStatus={true} />
                </div>
              </div>
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-[#16171f] border border-white/10 flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              </div>
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                ARIA — AI HR Interviewer
              </h1>
              <p className="text-white/40 text-sm">Senior Talent Acquisition, Skill Mind AI</p>
            </div>
          </div>

          <div className="space-y-8 text-left">
            {/* Candidate Profile Section */}
            <div>
              <h3 className="text-white/30 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Candidate Profile</h3>
              {fetchingStats ? (
                <div className="h-32 flex items-center justify-center bg-white/5 rounded-3xl border border-white/5">
                  <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  <span className="ml-3 text-white/40 text-sm">Loading profile...</span>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3 md:gap-4">
                  {[
                    { label: 'Resume Score', key: 'resume_strength', icon: BarChart, color: 'text-purple-400' },
                    { label: 'JD Match', key: 'jd_match', icon: Target, color: 'text-pink-400' },
                    { label: 'Quiz Score', key: 'quiz_score', icon: Zap, color: 'text-yellow-400' },
                    { label: 'Coding Score', key: 'coding_score', icon: Code, color: 'text-green-400' }
                  ].map((stat) => (
                    <div key={stat.label} className="bg-white/5 border border-white/5 p-4 rounded-2xl flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center ${stat.color}`}>
                        <stat.icon className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="text-white/20 text-[10px] font-bold uppercase">{stat.label}</p>
                        <p className="text-white font-bold text-lg">
                          {candidateStats?.report?.[stat.key] || 0}%
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Skills Overview */}
            <div>
              <h3 className="text-white/30 text-[10px] font-black uppercase tracking-[0.2em] mb-4">Skills Overview</h3>
              <div className="flex flex-wrap gap-2">
                {candidateStats?.skills?.length ? candidateStats.skills.map(skill => (
                  <span key={skill} className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 text-xs font-medium">
                    {skill}
                  </span>
                )) : (
                  <p className="text-white/20 text-xs italic">No specific skills detected yet.</p>
                )}
              </div>
            </div>

            {/* Meta Info */}
            <div className="flex flex-wrap items-center gap-y-2 gap-x-6 pt-4 border-t border-white/5">
              {[
                { label: '6 Questions', icon: MessageCircle },
                { label: '~15-20 mins', icon: Timer },
                { label: 'Voice + Text', icon: Mic },
                { label: 'GPT-4o Powered', icon: Brain }
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2 text-white/30">
                  <item.icon className="w-3.5 h-3.5" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">{item.label}</span>
                </div>
              ))}
            </div>

            {/* Action Button */}
            <button 
              onClick={handleJoin}
              disabled={loading}
              className="w-full h-16 rounded-2xl bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-bold text-lg flex items-center justify-center gap-3 transition-all active:scale-[0.98] shadow-lg shadow-blue-500/20"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Preparing Session...</span>
                </>
              ) : (
                <>
                  <div className="w-3 h-3 rounded-full bg-[#10b981] shadow-[0_0_10px_#10b981]" />
                  <span>Join Interview Now</span>
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // ── Main Layout (Google Meet Style) ──
  return (
    <div className="flex flex-col h-screen bg-[#0d0e14] text-[#e8eaed] font-['Plus_Jakarta_Sans'] overflow-hidden">
      
      {/* Top Navigation Bar */}
      <header className="h-16 flex items-center justify-between px-6 border-b border-white/5 z-20">
        <div className="flex items-center gap-4">
          <div className="bg-[#1a73e8] p-1.5 rounded-lg">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <h2 className="font-black tracking-tight flex items-center gap-2">
            SKILL MIND AI <span className="text-white/20">|</span> <span className="text-xs uppercase tracking-widest text-[#9aa0a6] font-bold">HR Interview Room</span>
          </h2>
          <div className="flex items-center gap-2 px-3 py-1 bg-red-500/10 rounded-full border border-red-500/20 ml-2">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-[10px] font-bold text-red-500 uppercase tracking-widest">● REC</span>
          </div>
        </div>

        <div className="flex items-center gap-3 bg-[#1c1e26] px-4 py-2 rounded-xl border border-white/10">
          <Timer className="w-4 h-4 text-[#9aa0a6]" />
          <span className="font-mono font-bold text-sm">{formatTime(time)}</span>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-[10px] font-black tracking-widest text-white/40 uppercase">Progress</p>
            <p className="text-xs font-bold font-mono">Q {questionNumber} / 6</p>
          </div>
          <div className="flex gap-1">
            {[1,2,3,4,5,6].map(n => (
              <div key={n} className={`w-6 h-1 rounded-full ${n < questionNumber ? 'bg-green-500' : n === questionNumber ? 'bg-blue-500 shadow-[0_0_8px_rgba(26,115,232,1)]' : 'bg-white/10'}`} />
            ))}
          </div>
        </div>
      </header>

      {/* Main View Area */}
      <main className="flex-1 flex p-6 gap-6 relative overflow-hidden">
        
        {/* LEFT: ARIA Focus (65%) */}
        <div className="flex-[0.65] relative bg-[#1c1e26] rounded-3xl overflow-hidden border border-white/10 shadow-inner flex items-center justify-center">
          <AriaAvatar state={ariaState} size={300} />
          
          <div className="absolute bottom-6 left-6 flex items-center gap-3 bg-black/60 backdrop-blur-md px-4 py-2 rounded-xl border border-white/10">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-500">
              <User className="w-4 h-4" />
            </div>
            <span className="text-sm font-bold">ARIA (AI Interviewer)</span>
          </div>

          <AnimatePresence>
            {ariaState === 'thinking' && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-3"
              >
                <div className="flex gap-1.5">
                  <motion.div animate={{ scale: [1, 1.5, 1] }} transition={{ repeat: Infinity, duration: 1 }} className="w-2 h-2 bg-blue-500 rounded-full" />
                  <motion.div animate={{ scale: [1, 1.5, 1] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-2 h-2 bg-blue-500 rounded-full" />
                  <motion.div animate={{ scale: [1, 1.5, 1] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-2 h-2 bg-blue-500 rounded-full" />
                </div>
                <p className="text-xs font-bold text-blue-500 uppercase tracking-widest">Evaluating...</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT: Candidate & Transcript (35%) */}
        <div className="flex-[0.35] flex flex-col gap-6">
          
          {/* Candidate Tile */}
          <div className="h-1/2 relative bg-[#1c1e26] rounded-3xl overflow-hidden border border-white/10 shadow-2xl">
            {isCamOn ? (
              <>
                <video 
                  ref={videoRef}
                  autoPlay 
                  muted 
                  playsInline 
                  className="w-full h-full object-cover scale-x-[-1]"
                />
                <canvas 
                  ref={canvasRef}
                  width={300}
                  height={100}
                  className="absolute bottom-16 left-0 w-full h-16 pointer-events-none"
                />
              </>
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center gap-4 bg-[#12141a] p-8 text-center">
                <div className="w-20 h-20 rounded-full bg-white/5 flex items-center justify-center text-white/20">
                  <User className="w-10 h-10" />
                </div>
                {errorMessage ? (
                    <p className="text-red-400 text-sm font-bold max-w-xs">{errorMessage}</p>
                ) : (
                    <p className="text-white/20 text-xs font-bold uppercase tracking-widest">Camera Off</p>
                )}
              </div>
            )}
            
            <div className="absolute bottom-4 left-4 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 flex items-center gap-2">
              {!isMicOn && <MicOff className="w-3 h-3 text-red-500" />}
              <span className="text-xs font-bold">You (Candidate)</span>
            </div>
          </div>

          {/* Transcript Panel */}
          <div className="h-1/2 bg-[#1c1e26] rounded-3xl border border-white/10 overflow-hidden flex flex-col shadow-2xl">
            <div className="p-4 border-b border-white/5 flex items-center justify-between">
              <h3 className="text-xs font-black uppercase tracking-widest text-white/40 flex items-center gap-2">
                <MessageCircle className="w-4 h-4" /> Live Transcript
              </h3>
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-4 font-['JetBrains_Mono'] scroll-smooth">
              {transcript.map((item, i) => (
                <motion.div 
                  initial={{ opacity: 0, x: item.role === 'ai' ? -10 : 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={i}
                  className={`flex flex-col ${item.role === 'ai' ? 'items-start' : 'items-end'}`}
                >
                  <p className="text-[10px] uppercase font-bold text-white/20 mb-1">{item.role === 'ai' ? 'ARIA' : 'YOU'}</p>
                  <div className={`p-3 rounded-2xl text-xs leading-relaxed max-w-[85%] ${
                    item.role === 'ai' ? 'bg-blue-500/10 text-blue-200 border border-blue-500/20' : 'bg-white/5 text-white/80 border border-white/5'
                  }`}>
                    {item.text}
                  </div>
                </motion.div>
              ))}
              
              {/* Live Subtitles */}
              {isListening && answerInput && (
                <motion.div 
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-end"
                >
                  <p className="text-[10px] uppercase font-bold text-blue-500 mb-1 flex items-center gap-1">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    Listening...
                  </p>
                  <div className="p-3 rounded-2xl text-xs leading-relaxed max-w-[85%] bg-blue-500/5 text-blue-300/60 border border-dashed border-blue-500/20 italic">
                    {answerInput}...
                  </div>
                </motion.div>
              )}
              <div ref={scrollRef} />
            </div>
          </div>

        </div>
      </main>

      {/* Bottom Control Bar */}
      <footer className="h-24 px-8 pb-6 bg-gradient-to-t from-black to-transparent z-20 flex items-center justify-between">
        <div className="flex gap-4">
          <button 
            onClick={() => {
              if (stream) {
                stream.getAudioTracks().forEach(t => t.enabled = !isMicOn);
                setIsMicOn(!isMicOn);
              }
            }}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all border ${isMicOn ? 'bg-white/10 border-white/10 hover:bg-white/20' : 'bg-red-500 border-red-500 shadow-[0_0_20px_rgba(234,67,53,0.4)]'}`}
          >
            {isMicOn ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
          </button>
          <button 
            onClick={() => {
              if (stream) {
                stream.getVideoTracks().forEach(t => t.enabled = !isCamOn);
                setIsCamOn(!isCamOn);
              }
            }}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all border ${isCamOn ? 'bg-white/10 border-white/10 hover:bg-white/20' : 'bg-red-500 border-red-500 shadow-[0_0_20px_rgba(234,67,53,0.4)]'}`}
          >
            {isCamOn ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
          </button>
        </div>

        <div className="flex-1 max-w-2xl px-8 relative">
          <input 
            type="text" 
            placeholder={isListening ? "Listening to your voice..." : "Type your answer here..."}
            value={answerInput}
            onChange={(e) => setAnswerInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            disabled={ariaState === 'speaking' || ariaState === 'thinking'}
            className="w-full bg-[#1c1e26] border border-white/10 focus:border-[#1a73e8] rounded-full px-6 py-4 pr-24 outline-none transition-all text-sm placeholder:text-white/20"
          />
          <div className="absolute right-12 top-1/2 -translate-y-1/2 flex items-center gap-2">
            <button 
              onClick={toggleSTT}
              className={`p-2 rounded-lg transition-all ${isListening ? 'text-red-500 animate-pulse' : 'text-white/40 hover:text-white'}`}
            >
              <Mic className="w-5 h-5" />
            </button>
            <button 
              onClick={handleSend}
              disabled={!answerInput.trim() || loading || ariaState === 'speaking' || ariaState === 'thinking'}
              className="p-2 bg-[#1a73e8] disabled:bg-white/5 text-white rounded-lg transition-all"
            >
              {loading ? (
                 <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-white/40 hover:bg-white/10 transition-all">
            <Settings className="w-5 h-5" />
          </button>
          <button className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-white/40 hover:bg-white/10 transition-all">
            <MoreVertical className="w-5 h-5" />
          </button>
          <button 
            onClick={() => window.confirm('End this interview session?') && window.location.reload()}
            className="flex items-center gap-3 px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-2xl font-black text-sm shadow-[0_0_30px_rgba(234,67,53,0.3)] transition-all"
          >
            <PhoneOff className="w-4 h-4" /> End Call
          </button>
        </div>
      </footer>
    </div>
  );
};

export default InterviewRoom;
