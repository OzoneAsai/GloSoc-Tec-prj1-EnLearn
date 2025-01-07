import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getPhase1Data } from '../services/api';
import Phase1Reading from '../components/Phase1Reading';

const Phase1Page = () => {
  const [rows, setRows] = useState([]);
  const [soundUrl, setSoundUrl] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getPhase1Data();
        setRows(data.rows);

        // If the API returns a sound URL in the future, set it here
        // For now, we leave this as null or a placeholder
        setSoundUrl(null);
      } catch (error) {
        console.error('Error fetching Phase1 data:', error);
      }
    };
    fetchData();
  }, []);

  const handleNext = () => {
    navigate('/phase2');
  };

  return (
    <div style={{ padding: '16px' }}>
      <Phase1Reading rows={rows} soundUrl={soundUrl} />
      <button onClick={handleNext}>Next Phase</button>
    </div>
  );
};

export default Phase1Page;
