export const en = {
  auth: {
    checkingAuthentication: 'Checking authentication...',
  },
  health: {
    status: {
      pass: 'All systems operational',
      warn: 'Some services have performance issues',
      fail: 'Critical system issues detected',
      default: 'System status unknown',
    },
  },
} as const;

export type Locale = typeof en;
