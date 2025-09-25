export type AppConfig = {
  brandTitle: string;
  brandSubtitle: string;
  appTitle: string;
  environment: string;
};

const fallbackBrandTitle = 'JEEX Plan';
const fallbackBrandSubtitle = 'Documentation Generator';

const toNonEmptyString = (value: string | undefined, fallback: string): string => {
  const trimmed = value?.trim();
  return trimmed && trimmed.length > 0 ? trimmed : fallback;
};

export const appConfig: AppConfig = {
  brandTitle: toNonEmptyString(import.meta.env.VITE_BRAND_TITLE, fallbackBrandTitle),
  brandSubtitle: toNonEmptyString(
    import.meta.env.VITE_BRAND_SUBTITLE,
    fallbackBrandSubtitle
  ),
  appTitle: toNonEmptyString(import.meta.env.VITE_APP_TITLE, fallbackBrandTitle),
  environment: toNonEmptyString(import.meta.env.VITE_ENVIRONMENT, 'development'),
};
