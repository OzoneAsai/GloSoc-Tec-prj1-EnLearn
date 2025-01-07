import React from 'react';
import { useNavigate } from 'react-router-dom';
import { startLearning } from '../services/api';

const StartPage = () => {
  const navigate = useNavigate();

  const handleStart = async () => {
    try {
      // Example: use a hard-coded seed
      await startLearning(42);
      navigate('/phase1');
    } catch (error) {
      console.error('Error starting learning:', error);
    }
  };

  return (
    <div style={{ padding: '16px' }}>
      <h1>Welcome to the Interactive Learning Tool</h1>
      <p>This demo shows a Phase-based English learning flow.</p>
      <button onClick={handleStart}>Start Learning</button>
    </div>
  );
};

export default StartPage;
