import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { SecurityProvider } from './context/SecurityContext';
import { AppRoutes } from './routes/AppRoutes';

export const App: React.FC = () => {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '') || '/'}>
      <SecurityProvider>
        <AppRoutes />
      </SecurityProvider>
    </BrowserRouter>
  );
};

export default App;
