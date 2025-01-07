import React from 'react';
import { useNavigate } from 'react-router-dom';

const SummaryPage = () => {
  const navigate = useNavigate();

  const handleRestart = () => {
    navigate('/');
  };

  return (
    <div style={{ padding: '16px' }}>
      <h2>Congratulations! You've completed the training.</h2>
      <p>Feel free to restart or explore other features.</p>
      <button onClick={handleRestart}>Restart Learning</button>
    </div>
  );
};

export default SummaryPage;
