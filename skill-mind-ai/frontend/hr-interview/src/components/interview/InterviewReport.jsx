import React from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle2, AlertCircle, Award, 
  Target, Zap, MessageSquare, Download,
  ArrowRight, ThumbsUp, BarChart3
} from 'lucide-react';

const InterviewReport = ({ report, qaLog, onRestart }) => {
  if (!report) return null;

  const getScoreColor = (score) => {
    if (score >= 75) return 'text-green-500';
    if (score >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getReadinessIcon = (level) => {
    if (level === 'Strong') return <CheckCircle2 className="w-6 h-6 text-green-500" />;
    if (level === 'Moderate') return <AlertCircle className="w-6 h-6 text-yellow-500" />;
    return <AlertCircle className="w-6 h-6 text-red-500" />;
  };

  return (
    <div className="min-h-screen bg-[#0d0e14] text-[#e8eaed] p-8 font-['Plus_Jakarta_Sans'] overflow-y-auto">
      <div className="max-w-5xl mx-auto">
        
        {/* Header Section */}
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-4xl font-black tracking-tight mb-2">Interview <span className="text-[#1a73e8]">Evaluation</span></h1>
            <p className="text-[#9aa0a6]">ARIA's comprehensive feedback for your performance.</p>
          </div>
          <div className="flex gap-4">
            <button className="flex items-center gap-2 px-6 py-3 bg-white/5 hover:bg-white/10 rounded-2xl border border-white/10 transition-all font-bold text-sm">
              <Download className="w-4 h-4" /> Download PDF
            </button>
            <button 
              onClick={onRestart}
              className="flex items-center gap-2 px-6 py-3 bg-[#1a73e8] hover:bg-[#1a73e8]/90 rounded-2xl shadow-lg transition-all font-bold text-sm"
            >
              Back to Dashboard <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Hero Score Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          
          {/* Main Score Circle */}
          <div className="col-span-1 md:col-span-1 bg-[#16171f] border border-white/10 rounded-[2.5rem] p-8 flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute top-0 left-0 w-full h-1 bg-[#1a73e8]" />
            <p className="text-[#9aa0a6] text-xs font-black uppercase tracking-[0.2em] mb-6">Overall Readiness</p>
            <div className="relative w-40 h-40 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="80" cy="80" r="70" stroke="currentColor" strokeWidth="8" fill="transparent" className="text-white/5" />
                <motion.circle 
                  cx="80" cy="80" r="70" stroke="currentColor" strokeWidth="8" fill="transparent" 
                  strokeDasharray={440}
                  initial={{ strokeDashoffset: 440 }}
                  animate={{ strokeDashoffset: 440 - (440 * report.hr_interview_score) / 100 }}
                  transition={{ duration: 2, ease: "easeOut" }}
                  className="text-[#1a73e8]"
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-4xl font-black">{Math.round(report.hr_interview_score)}%</span>
                <span className="text-[10px] text-[#9aa0a6] uppercase font-bold tracking-widest">Score</span>
              </div>
            </div>
            <div className="mt-6 flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full border border-white/10">
              {getReadinessIcon(report.readiness_level)}
              <span className={`text-sm font-bold ${getScoreColor(report.hr_interview_score)}`}>{report.readiness_level}</span>
            </div>
          </div>

          {/* AI Summary */}
          <div className="col-span-1 md:col-span-2 bg-[#16171f] border border-white/10 rounded-[2.5rem] p-10 relative overflow-hidden">
            <MessageSquare className="absolute top-8 right-8 w-20 h-20 text-white/5" />
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
              <Brain className="w-6 h-6 text-[#1a73e8]" /> ARIA's Executive Summary
            </h3>
            <div className="space-y-4 text-white/70 leading-relaxed text-sm">
              {report.ai_summary.split('\n').map((para, i) => (
                <p key={i}>{para}</p>
              ))}
            </div>
          </div>
        </div>

        {/* Radar/Bar Dimensions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12">
          
          {/* Performance Dimensions */}
          <div className="bg-[#16171f] border border-white/10 rounded-[2.5rem] p-8">
            <h3 className="text-lg font-bold mb-8 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-[#1a73e8]" /> Breakdown by Dimension
            </h3>
            <div className="space-y-8">
              {[
                { label: 'Behavioral', score: report.behavioral_rating, color: '#1a73e8' },
                { label: 'Communication', score: report.communication_rating, color: '#34a853' },
                { label: 'Technical', score: report.technical_rating, color: '#fbbc05' },
                { label: 'Confidence', score: report.confidence_index, color: '#ea4335' }
              ].map((dim, i) => (
                <div key={i}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-bold text-[#9aa0a6]">{dim.label}</span>
                    <span className="text-sm font-black font-mono">{dim.score}/10</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${dim.score * 10}%` }}
                      transition={{ duration: 1, delay: 0.5 + i * 0.1 }}
                      className="h-full rounded-full"
                      style={{ backgroundColor: dim.color }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Strengths & Improvements */}
          <div className="flex flex-col gap-8">
             <div className="bg-[#16171f] border border-white/10 rounded-[2.5rem] p-8 flex-1">
                <h3 className="text-sm font-black uppercase tracking-widest text-green-500 mb-6 flex items-center gap-2">
                  <ThumbsUp className="w-4 h-4" /> Key Strengths
                </h3>
                <div className="flex flex-wrap gap-2">
                  {report.top_strengths.map((s, i) => (
                    <span key={i} className="px-4 py-2 bg-green-500/10 border border-green-500/20 rounded-xl text-green-400 text-xs font-bold">
                      {s}
                    </span>
                  ))}
                </div>
             </div>
             <div className="bg-[#16171f] border border-white/10 rounded-[2.5rem] p-8 flex-1">
                <h3 className="text-sm font-black uppercase tracking-widest text-[#1a73e8] mb-6 flex items-center gap-2">
                  <Target className="w-4 h-4" /> Targeted Recommendations
                </h3>
                <p className="text-sm italic text-white/50">{report.recommendation}</p>
             </div>
          </div>
        </div>

        {/* Detailed QA History */}
        <div className="bg-[#16171f] border border-white/10 rounded-[2.5rem] overflow-hidden mb-12">
          <div className="p-8 border-b border-white/5">
            <h3 className="text-lg font-bold">Detailed Question Log</h3>
          </div>
          <div className="divide-y divide-white/5">
            {qaLog.map((qa, i) => (
              <div key={i} className="p-8 hover:bg-white/[0.02] transition-colors">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-start gap-4">
                    <span className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center font-bold text-xs">Q{i+1}</span>
                    <p className="font-bold text-white max-w-2xl">{qa.question}</p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-black font-mono text-[#1a73e8] bg-blue-500/10 px-3 py-1 rounded-full">{qa.score}/100</span>
                  </div>
                </div>
                <div className="ml-12">
                  <div className="bg-black/20 p-4 rounded-2xl border border-white/5 mb-4 italic text-sm text-[#9aa0a6]">
                    "{qa.answer}"
                  </div>
                  <p className="text-xs text-white/40 flex items-center gap-2">
                    <Zap className="w-3 h-3" /> {qa.feedback}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

export default InterviewReport;
