import { useContext } from 'react';
import { LoginFeaturesConfigContext } from './LoginFeaturesContext';
import {
  defaultLoginFeaturesConfig,
  type LoginFeaturesConfig,
} from '../config/loginFeaturesConfig';

export const useLoginFeaturesConfig = (): LoginFeaturesConfig => {
  const context = useContext(LoginFeaturesConfigContext);
  return context ?? defaultLoginFeaturesConfig;
};

export { defaultLoginFeaturesConfig };
