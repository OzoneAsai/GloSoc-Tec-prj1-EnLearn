import React from 'react';
import { Routes, Route } from 'react-router-dom';
import StartPage from '../pages/StartPage';
import Phase1Page from '../pages/Phase1Page';
import Phase2Page from '../pages/Phase2Page';
import SummaryPage from '../pages/SummaryPage';

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<StartPage />} />
      <Route path="/phase1" element={<Phase1Page />} />
      <Route path="/phase2" element={<Phase2Page />} />
      <Route path="/summary" element={<SummaryPage />} />
    </Routes>
  );
};

export default AppRoutes;
