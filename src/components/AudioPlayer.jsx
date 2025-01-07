import React from 'react';

const AudioPlayer = ({ src }) => {
  if (!src) {
    return <div style={{ color: 'gray' }}>No audio available</div>;
  }

  return (
    <div>
      <audio controls>
        <source src={src} type="audio/mpeg" />
        Your browser does not support the audio element.
      </audio>
    </div>
  );
};

export default AudioPlayer;
