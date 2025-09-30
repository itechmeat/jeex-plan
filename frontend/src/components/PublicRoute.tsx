import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AUTH_MESSAGES } from '../config/constants';
import { ROUTES } from '../config/routes';
import { useAuth } from '../contexts/useAuth';
import { hasValidFromProperty, isValidRedirectPath } from '../utils/validation';
import styles from './AuthLoader.module.css';

interface PublicRouteProps {
  children: React.ReactNode;
  redirectTo?: string;
}

export const PublicRoute: React.FC<PublicRouteProps> = ({
  children,
  redirectTo = ROUTES.DASHBOARD,
}) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

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
    // Validate and sanitize the redirect target to prevent open redirect vulnerability
    let finalRedirectTo = redirectTo;

    if (hasValidFromProperty(location.state)) {
      const fromPath = location.state.from.pathname;
      // Only allow safe relative paths
      if (isValidRedirectPath(fromPath)) {
        finalRedirectTo = fromPath;
      } else {
        console.warn(
          `Invalid redirect path detected: "${fromPath}". Redirecting to default.`
        );
      }
    }

    return <Navigate to={finalRedirectTo} replace />;
  }

  return <>{children}</>;
};
