import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AUTH_MESSAGES } from '../config/constants';
import { ROUTES } from '../config/routes';
import { useAuth } from '../contexts/useAuth';
import styles from './AuthLoader.module.css';

interface PublicRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

type LoginLocationState = {
  from?: {
    pathname?: string;
  };
};

export const PublicRoute: React.FC<PublicRouteProps> = ({
  children,
  redirectTo = ROUTES.DASHBOARD,
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();
  const locationState = location.state as LoginLocationState | undefined;

  if (isLoading) {
    return (
      <div className={styles.loaderContainer}>
        <div className={styles.spinner} />
        <p className={styles.message} role='status' aria-live='polite'>
          {AUTH_MESSAGES.CHECKING_AUTHENTICATION}
        </p>
      </div>
    );
  }

  if (isAuthenticated) {
    // For login page, respect the 'from' location if available
    const finalRedirectTo =
      typeof locationState?.from?.pathname === 'string'
        ? locationState.from.pathname
        : redirectTo;

    return <Navigate to={finalRedirectTo} replace />;
  }

  return <>{children}</>;
};
