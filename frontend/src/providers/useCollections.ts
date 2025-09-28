import { useContext } from 'react';
import {
  documentsCollection,
  healthStatusCollection,
  projectsCollection,
  systemMetricsCollection,
} from './collections';
import { DBContext } from './context';

export const useCollections = () => {
  const context = useContext(DBContext);
  if (!context) {
    throw new Error('useCollections must be used within a DBProvider');
  }
  return context;
};

export {
  healthStatusCollection,
  systemMetricsCollection,
  projectsCollection,
  documentsCollection,
};
