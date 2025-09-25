import type { Locale } from './en';
import { en } from './en';

type TranslateOptions = {
  fallbackKey?: string;
  defaultValue?: string;
};

const defaultLocale: Locale = en;

const getLocalizedValue = (
  key: string,
  source: Locale | Record<string, unknown>
): string | undefined => {
  const segments = key.split('.');
  let current: unknown = source;

  for (const segment of segments) {
    if (
      typeof current !== 'object' ||
      current === null ||
      !(segment in (current as Record<string, unknown>))
    ) {
      return undefined;
    }

    current = (current as Record<string, unknown>)[segment];
  }

  return typeof current === 'string' ? current : undefined;
};

export const t = (key: string, options?: TranslateOptions): string => {
  const localized = getLocalizedValue(key, defaultLocale);

  if (localized !== undefined) {
    return localized;
  }

  if (options?.fallbackKey) {
    const fallback = getLocalizedValue(options.fallbackKey, defaultLocale);
    if (fallback !== undefined) {
      return fallback;
    }
  }

  if (options?.defaultValue !== undefined) {
    return options.defaultValue;
  }

  return key;
};
