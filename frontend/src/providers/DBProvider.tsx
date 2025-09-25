import React from 'react';
import { collections } from './collections';
import { DBContext } from './context';

// Provider component
interface DBProviderProps {
  children: React.ReactNode;
}

export const DBProvider: React.FC<DBProviderProps> = ({ children }) => {
  return <DBContext.Provider value={collections}>{children}</DBContext.Provider>;
};
