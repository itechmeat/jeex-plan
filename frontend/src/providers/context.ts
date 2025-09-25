import React from 'react';
import { collections } from './collections';

// Context for accessing collections
export const DBContext = React.createContext<typeof collections | null>(null);
