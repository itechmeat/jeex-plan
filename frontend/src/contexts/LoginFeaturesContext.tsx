import React, { createContext, ReactNode } from 'react';
import { LoginFeaturesConfig } from '../config/loginFeaturesConfig';

type LoginFeaturesProviderProps = {
  value: LoginFeaturesConfig;
  children: ReactNode;
};

const LoginFeaturesConfigContext = createContext<LoginFeaturesConfig | null>(null);

export const LoginFeaturesProvider: React.FC<LoginFeaturesProviderProps> = ({
  value,
  children,
}) => (
  <LoginFeaturesConfigContext.Provider value={value}>
    {children}
  </LoginFeaturesConfigContext.Provider>
);

export { LoginFeaturesConfigContext };
