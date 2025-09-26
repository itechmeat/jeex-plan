import { useContext } from 'react';
import { DBContext } from './context';
import { healthStatusCollection, systemMetricsCollection } from './collections';

export const useCollections = () => {
  const context = useContext(DBContext);
  if (!context) {
    throw new Error('useCollections must be used within a DBProvider');
  }
  return context;
};

export { healthStatusCollection, systemMetricsCollection };
