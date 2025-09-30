export type AppConfig = {
  brandTitle: string;
  brandSubtitle: string;
  appTitle: string;
  environment: string;
};

const validateRequiredEnv = (value: string | undefined, name: string): string => {
  const trimmed = value?.trim();
  if (!trimmed || trimmed.length === 0) {
    throw new Error(`Required environment variable ${name} is not set or empty`);
  }
  return trimmed;
};

export const appConfig: AppConfig = {
  brandTitle: validateRequiredEnv(import.meta.env.VITE_BRAND_TITLE, 'VITE_BRAND_TITLE'),
  brandSubtitle: validateRequiredEnv(
    import.meta.env.VITE_BRAND_SUBTITLE,
    'VITE_BRAND_SUBTITLE'
  ),
  appTitle: validateRequiredEnv(import.meta.env.VITE_APP_TITLE, 'VITE_APP_TITLE'),
  environment: validateRequiredEnv(
    import.meta.env.VITE_ENVIRONMENT,
    'VITE_ENVIRONMENT'
  ),
};
