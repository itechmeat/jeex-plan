/**
 * Application-wide constants and configuration values
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
