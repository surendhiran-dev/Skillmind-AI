import React, { useState } from 'react';
import InterviewRoom from './components/interview/InterviewRoom';
import InterviewReport from './components/interview/InterviewReport';
import { AnimatePresence, motion } from 'framer-motion';

function App() {
  const [reportData, setReportData] = useState(null);

  const handleComplete = (data) => {
    // data is { report, qa_log }
    setReportData(data);
  };

  const handleRestart = () => {
    setReportData(null);
    // Ideally redirect to dashboard or reload
    window.location.href = '/'; 
  };

  return (
    <div className="min-h-screen bg-[#0d0e14] text-white">
      <AnimatePresence mode="wait">
        {!reportData ? (
          <motion.div
            key="interview"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-screen"
          >
            <InterviewRoom onComplete={handleComplete} />
          </motion.div>
        ) : (
          <motion.div
            key="report"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="min-h-screen overflow-y-auto"
          >
            <InterviewReport 
              report={reportData.report} 
              qaLog={reportData.qa_log} 
              onRestart={handleRestart} 
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
