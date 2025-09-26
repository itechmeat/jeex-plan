export const ROUTES = {
  LOGIN: '/login',
  DASHBOARD: '/dashboard',
  PROJECTS: '/projects',
  PROJECTS_NEW: '/projects/new',
  HEALTH: '/health',
  TERMS: '/terms',
  PRIVACY: '/privacy',
  SUPPORT: '/support',
} as const;

export type RouteKey = keyof typeof ROUTES;
export type RoutePath = (typeof ROUTES)[RouteKey];
