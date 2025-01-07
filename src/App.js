import React from 'react';
import { BrowserRouter as Router } from 'react-router-dom';
import AppRoutes from './routes/AppRoutes';
import AppContextProvider from './context/AppContext';

const App = () => {
  return (
    <AppContextProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AppContextProvider>
  );
};

export default App;
