import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPhase2Data, nextPhase } from '../services/api';
import Phase2Masking from '../components/Phase2Masking';

const Phase2Page = () => {
  const [maskedRows, setMaskedRows] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchMaskedData = async () => {
      try {
        const data = await getPhase2Data();
        setMaskedRows(data.rows);
      } catch (error) {
        console.error('Error fetching Phase2 data:', error);
      }
    };
    fetchMaskedData();
  }, []);

  const handleNext = async () => {
    try {
      const response = await nextPhase();
      if (response.phase === 1) {
        // Phase reset, go to Phase1
        navigate('/phase1');
      } else if (response.phase === 'complete') {
        // Or if the back end indicates we're done
        navigate('/summary');
      } else {
        // Otherwise loop back to Phase1 or handle other logic
        navigate('/phase1');
      }
    } catch (error) {
      console.error('Error moving to next phase:', error);
    }
  };

  return (
    <div style={{ padding: '16px' }}>
      <Phase2Masking maskedRows={maskedRows} />
      <button onClick={handleNext}>Next Phase</button>
    </div>
  );
};

export default Phase2Page;
