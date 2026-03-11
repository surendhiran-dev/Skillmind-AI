import { useState, useCallback } from 'react';
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:5000/api/interview',
});

// Add JWT token interceptor
api.interceptors.request.use((config) => {
  let token = sessionStorage.getItem('token');
  
  // Storage fallback: Try URL parameters if sessionStorage is blocked or empty
  if (!token) {
    const params = new URLSearchParams(window.location.search);
    token = params.get('token');
    if (token) {
      console.log('useInterviewEngine: Retrieved token from URL fallback');
    }
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const useInterviewEngine = () => {
  const [transcript, setTranscript] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [sessionToken, setSessionToken] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [isComplete, setIsComplete] = useState(false);
  const [loading, setLoading] = useState(false);
  const [questionNumber, setQuestionNumber] = useState(0);

  const startInterview = useCallback(async (userId) => {
    setLoading(true);
    try {
      const { data } = await api.post('/start', { user_id: userId });
      const { token, session_id, response } = data;
      
      setSessionToken(token);
      setSessionId(session_id);
      setCurrentQuestion(response);
      setQuestionNumber(1);
      
      const fullText = response.acknowledgment 
        ? `${response.acknowledgment} ${response.question}`
        : response.question;
        
      setTranscript([{ role: 'ai', text: fullText, type: 'question' }]);
      return data;
    } catch (error) {
      console.error('Failed to start ARIA interview:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const submitAnswer = useCallback(async (answer, lastQuestionText) => {
    if (!sessionToken) return null;
    
    setLoading(true);
    // Add user answer to transcript immediately for UI snappiness
    setTranscript(prev => [...prev, { role: 'user', text: answer }]);
    
    try {
      const { data } = await api.post('/answer', { 
        token: sessionToken, 
        answer: answer,
        question_text: lastQuestionText
      });
      
      const { status, evaluation, next_question, report, question_number } = data;
      
      if (status === 'complete') {
        setIsComplete(true);
        // We'll show the report after this
        return { status: 'complete', evaluation, report };
      }
      
      // Handle next question
      const fullText = next_question.acknowledgment 
        ? `${next_question.acknowledgment} ${next_question.question}`
        : next_question.question;
        
      setTranscript(prev => [...prev, { role: 'ai', text: fullText, type: 'question', evaluation }]);
      setCurrentQuestion(next_question);
      setQuestionNumber(question_number);
      
      return { status: 'continue', evaluation, next_question };
    } catch (error) {
      console.error('Failed to submit ARIA answer:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

  const getReport = useCallback(async (sId) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/report/${sId || sessionId}`);
      return data;
    } catch (error) {
      console.error('Failed to fetch ARIA report:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return {
    transcript,
    currentQuestion,
    sessionToken,
    sessionId,
    isComplete,
    loading,
    questionNumber,
    startInterview,
    submitAnswer,
    getReport
  };
};
