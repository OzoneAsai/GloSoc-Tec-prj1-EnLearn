import React from 'react';
import AudioPlayer from './AudioPlayer';

const Phase1Reading = ({ rows, soundUrl }) => {
  return (
    <div>
      <h2>Phase1: Listen and Read</h2>
      <AudioPlayer src={soundUrl} />
      <ul>
        {rows.map((item, index) => (
          <li key={index}>
            <strong>English:</strong> {item.English}<br />
            <strong>Japanese:</strong> {item.Japanese}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default Phase1Reading;
