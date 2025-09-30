/**
 * Application-wide constants and configuration values
 *
 * NOTE: These strings are currently hardcoded in English.
 * Future enhancement: Replace with i18n keys when internationalization is implemented.
 * Example: CHECKING_AUTHENTICATION: t('auth.checking') instead of the literal string.
 */

export const AUTH_MESSAGES = {
  CHECKING_AUTHENTICATION: 'Checking authentication...',
  AUTHENTICATION_REQUIRED: 'Authentication required',
  SESSION_EXPIRED: 'Your session has expired',
} as const;

export const LOADING_MESSAGES = {
  LOADING: 'Loading...',
  PLEASE_WAIT: 'Please wait...',
} as const;

export const ERROR_MESSAGES = {
  GENERIC_ERROR: 'An error occurred',
  NETWORK_ERROR: 'Network error. Please check your connection.',
  UNAUTHORIZED: 'You are not authorized to access this resource',
} as const;
