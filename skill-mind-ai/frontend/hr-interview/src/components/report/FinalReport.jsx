import React, { useRef } from 'react';
import { motion } from 'framer-motion';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Cell, Legend
} from 'recharts';
import { Download, GraduationCap, Award, MessageCircle, BarChart3, TrendingUp, CheckCircle, BrainCircuit } from 'lucide-react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

const FinalReport = ({ reportData, onRestart }) => {
  const reportRef = useRef();

  // Data pre-processing for charts
  const metricsData = [
    { name: 'Relevance', value: reportData.avg_metrics.relevance * 10, full: 100 },
    { name: 'Depth', value: reportData.avg_metrics.depth * 10, full: 100 },
    { name: 'Comm.', value: reportData.avg_metrics.communication * 10, full: 100 },
    { name: 'Confidence', value: reportData.avg_metrics.confidence * 10, full: 100 },
  ];

  const exportPDF = async () => {
    const canvas = await html2canvas(reportRef.current, { scale: 2, backgroundColor: '#0f0c29' });
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF('p', 'mm', 'a4');
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
    pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    pdf.save('SkillMind_AI_Interview_Report.pdf');
  };

  const getReadinessColor = (readiness) => {
    if (readiness.includes('Strong')) return 'text-green-400';
    if (readiness.includes('Moderate')) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="min-h-screen bg-[#0f0c29] text-white p-4 md:p-8 overflow-y-auto scrollbar-hide">
      <div className="max-w-6xl mx-auto" ref={reportRef}>
        
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12">
          <div>
            <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="flex items-center gap-3 mb-2">
              <div className="w-10 h-10 bg-primary/20 rounded-lg flex items-center justify-center">
                <BrainCircuit className="text-primary w-6 h-6" />
              </div>
              <span className="text-sm font-bold tracking-[0.3em] text-white/40 uppercase">SkillMind AI Performance</span>
            </motion.div>
            <h1 className="text-5xl font-black italic tracking-tighter">
              INTERVIEW <span className="text-primary">ANALYTICS</span>
            </h1>
          </div>
          
          <div className="flex gap-4">
            <button 
              onClick={exportPDF}
              className="px-6 py-3 bg-white/5 border border-white/10 rounded-2xl flex items-center gap-2 hover:bg-white/10 transition-all font-bold text-sm"
            >
              <Download className="w-4 h-4" /> Download Report
            </button>
            <button 
              onClick={onRestart}
              className="px-6 py-3 bg-primary text-white rounded-2xl shadow-neon hover:scale-105 transition-all font-bold text-sm"
            >
              New Interview
            </button>
          </div>
        </header>

        {/* Top Grid: Summary Highlights */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {[
            { label: 'Final Score', value: `${Math.round(reportData.final_hr_score)}/100`, icon: Award, color: 'text-primary' },
            { label: 'Readiness', value: reportData.readiness_level.split(':')[1]?.trim() || reportData.readiness_level, icon: GraduationCap, color: getReadinessColor(reportData.readiness_level) },
            { label: 'Efficiency', value: '88%', icon: TrendingUp, color: 'text-accent' },
            { label: 'Questions', value: reportData.conversation.filter(m => m.role === 'ai').length, icon: MessageCircle, color: 'text-blue-400' }
          ].map((stat, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-glass border border-glass-border p-6 rounded-3xl"
            >
              <div className="flex items-center gap-3 mb-3 text-white/40">
                <stat.icon className="w-4 h-4" />
                <span className="text-[10px] font-bold uppercase tracking-widest">{stat.label}</span>
              </div>
              <div className={`text-3xl font-black ${stat.color}`}>{stat.value}</div>
            </motion.div>
          ))}
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Bar Chart: Core Metrics */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-glass border border-glass-border p-8 rounded-[2rem]"
          >
            <div className="flex items-center gap-2 mb-8">
              <BarChart3 className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-bold uppercase tracking-tighter">Competency Breakdown</h3>
            </div>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={metricsData} margin={{ top: 20, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }} />
                  <YAxis hide domain={[0, 100]} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: 'none', background: '#1e272e', color: '#fff' }}
                    itemStyle={{ color: '#00d4ff', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="value" radius={[10, 10, 0, 0]}>
                    {metricsData.map((entry, index) => (
                      <Cell key={index} fill={index % 2 === 0 ? '#00d4ff' : '#00ffd4'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Radar Chart: Skill Profile */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="bg-glass border border-glass-border p-8 rounded-[2rem]"
          >
            <div className="flex items-center gap-2 mb-8">
              <BrainCircuit className="w-5 h-5 text-accent" />
              <h3 className="text-lg font-bold uppercase tracking-tighter">Skill Profile</h3>
            </div>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={metricsData}>
                  <PolarGrid stroke="rgba(255,255,255,0.1)" />
                  <PolarAngleAxis dataKey="name" tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 10 }} />
                  <Radar
                    name="Candidate"
                    dataKey="value"
                    stroke="#00d4ff"
                    fill="#00d4ff"
                    fillOpacity={0.4}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        </div>

        {/* Detailed Insights */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Feedback Card */}
          <div className="lg:col-span-2 bg-glass border border-glass-border p-8 rounded-[2rem]">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-3">
              <CheckCircle className="text-green-400 w-6 h-6" />
              Strategic Feedback & Recommendations
            </h3>
            <div className="space-y-6">
              {reportData.avg_metrics.relevance < 7 && (
                <div className="flex gap-4 p-4 bg-red-400/10 border border-red-400/20 rounded-2xl">
                  <span className="text-2xl">💡</span>
                  <div>
                    <h4 className="font-bold text-red-400 text-sm uppercase">Improve Relevance</h4>
                    <p className="text-sm text-white/60">Your answers were slightly off-topic. Focus directly on the interviewer's question before expanding.</p>
                  </div>
                </div>
              )}
              <div className="flex gap-4 p-4 bg-primary/10 border border-primary/20 rounded-2xl">
                <span className="text-2xl">✅</span>
                <div>
                  <h4 className="font-bold text-primary text-sm uppercase">Expert Insight</h4>
                  <p className="text-sm text-white/60">Based on your performance, you demonstrate strong {metricsData.sort((a,b) => b.value - a.value)[0].name} skills.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-glass border border-glass-border p-8 rounded-[2rem] flex flex-col justify-center items-center text-center">
             <div className="w-24 h-24 rounded-full border-4 border-primary border-t-transparent animate-spin-slow mb-4 flex items-center justify-center">
                <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center">
                  <TrendingUp className="text-primary w-8 h-8" />
                </div>
             </div>
             <h4 className="text-lg font-bold mb-2">Growth Mindset</h4>
             <p className="text-xs text-white/40 italic">"Technology is just a tool. In people, we build the future."</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FinalReport;
