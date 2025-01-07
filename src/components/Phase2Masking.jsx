import React, { useState } from 'react';
import { checkAnswer } from '../services/api';

const Phase2Masking = ({ maskedRows }) => {
  const [answers, setAnswers] = useState({});
  const [feedback, setFeedback] = useState(null);

  // For each row, we only handle a single input here for demo.
  // If multiple masks exist, you'll need multiple inputs.
  const handleChange = (e, index) => {
    setAnswers({ ...answers, [index]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (maskedRows.length === 0) {
      return;
    }

    try {
      // For simplicity, let's check only the first row in detail.
      // In a real scenario, you'd want to send all masked items.
      const payload = {
        // Example payload format for the back end:
        original_english: maskedRows[0].original_english,
        masked_english: maskedRows[0].masked_english,
        answers: Object.values(answers) // e.g. an array of strings
      };

      const response = await checkAnswer(payload);
      setFeedback(response.feedback);
    } catch (error) {
      console.error('Error checking answers:', error);
    }
  };

  return (
    <div>
      <h2>Phase2: Fill in the Blanks</h2>
      {maskedRows.map((item, index) => (
        <div key={index} style={{ marginBottom: '1rem' }}>
          <p>{item.masked_english}</p>
          <input
            type="text"
            placeholder="Your answer..."
            value={answers[index] || ''}
            onChange={(e) => handleChange(e, index)}
          />
        </div>
      ))}

      <button onClick={handleSubmit}>Check Answers</button>

      {feedback && (
        <div style={{ marginTop: '1rem', fontWeight: 'bold' }}>
          Feedback: {feedback}
        </div>
      )}
    </div>
  );
};

export default Phase2Masking;
