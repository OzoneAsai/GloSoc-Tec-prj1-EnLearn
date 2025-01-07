import React, { createContext, useState } from 'react';

export const AppContext = createContext();

const AppContextProvider = ({ children }) => {
  const [appState, setAppState] = useState({
    // You can store any global data here, e.g. user info, current phase, etc.
    user: null,
    phase: 1,
  });

  return (
    <AppContext.Provider value={{ appState, setAppState }}>
      {children}
    </AppContext.Provider>
  );
};

export default AppContextProvider;
