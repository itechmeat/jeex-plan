import { useContext } from 'react';
import {
  defaultLoginFeaturesConfig,
  type LoginFeaturesConfig,
} from '../config/loginFeaturesConfig';
import { LoginFeaturesConfigContext } from './LoginFeaturesContext';

export const useLoginFeaturesConfig = (): LoginFeaturesConfig => {
  const context = useContext(LoginFeaturesConfigContext);
  return context ?? defaultLoginFeaturesConfig;
};

export { defaultLoginFeaturesConfig };
