import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button/Button';
import { Input } from '../../components/ui/Input/Input';
import { useAuth } from '../../contexts/useAuth';
import { useLoginFeaturesConfig } from '../../contexts/useLoginFeatures';
import styles from './Login.module.css';

type FeatureIconProps = {
  icon: string;
  label: string;
};

const FeatureIcon: React.FC<FeatureIconProps> = ({ icon, label }) => (
  <span className={styles.featureIcon} role='img' aria-label={label}>
    {icon}
  </span>
);

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, error: authError, clearError } = useAuth();
  const {
    title: featuresTitle,
    subtitle: featuresSubtitle,
    features,
  } = useLoginFeaturesConfig();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isLoading = isSubmitting;

  // Clear auth errors when component mounts
  useEffect(() => {
    clearError();
  }, [clearError]);

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange =
    (field: keyof typeof formData) => (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setFormData(prev => ({ ...prev, [field]: value }));

      if (errors[field]) {
        setErrors(prev => ({ ...prev, [field]: '' }));
      }

      if (authError) {
        clearError();
      }
    };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prevent multiple submissions
    if (isSubmitting) {
      return;
    }

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    const minLoadingTime = Number(import.meta.env.VITE_MIN_LOADING_TIME_MS) || 100;
    const startTime = Date.now();

    try {
      await login({
        email: formData.email.trim(),
        password: formData.password,
      });
    } catch (error) {
      // Error is handled by AuthContext, but ensure we wait for it to propagate
      console.error('Login submission error:', error);
    } finally {
      const elapsedTime = Date.now() - startTime;
      if (elapsedTime < minLoadingTime) {
        await new Promise(resolve => setTimeout(resolve, minLoadingTime - elapsedTime));
      }
      setIsSubmitting(false);
    }
  };

  // Handle Enter key submission
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      e.preventDefault();
      const form = e.currentTarget.closest('form');
      if (form) {
        // Use dispatchEvent for better test compatibility
        const submitEvent = new Event('submit', { bubbles: true, cancelable: true });
        form.dispatchEvent(submitEvent);
      }
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCard}>
        <div className={styles.header}>
          <h1 className={styles.title}>Welcome to JEEX Plan</h1>
          <p className={styles.subtitle}>Sign in to your account to continue</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className={styles.form}
          noValidate
          data-testid='login-form'
          onKeyDown={handleKeyDown}
        >
          {authError && (
            <div
              className={styles.errorBanner}
              role='alert'
              data-testid='error-message'
              aria-live='polite'
            >
              {authError}
            </div>
          )}

          <Input
            label='Email Address'
            type='email'
            value={formData.email}
            onChange={handleInputChange('email')}
            error={errors.email}
            placeholder='Enter your email'
            autoComplete='email'
            fullWidth
            data-testid='email-input'
            disabled={isLoading}
            onKeyDown={handleKeyDown}
          />

          <Input
            label='Password'
            type='password'
            value={formData.password}
            onChange={handleInputChange('password')}
            error={errors.password}
            placeholder='Enter your password'
            autoComplete='current-password'
            fullWidth
            data-testid='password-input'
            disabled={isLoading}
            onKeyDown={handleKeyDown}
          />

          <Button
            type='submit'
            variant='primary'
            size='lg'
            isLoading={isLoading}
            disabled={isLoading}
            fullWidth
            data-testid='sign-in-button'
            aria-busy={isLoading}
            onClick={e => {
              // Prevent multiple clicks during loading
              if (isLoading) {
                e.preventDefault();
                e.stopPropagation();
                return;
              }
            }}
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </Button>
        </form>

        <div className={styles.footer}>
          <p className={styles.footerText}>
            Don't have an account?{' '}
            <button
              type='button'
              className={styles.linkButton}
              onClick={() => navigate('/register')}
              data-testid='register-link'
            >
              Sign up here
            </button>
          </p>

          <p className={styles.footerText}>
            <button
              type='button'
              className={styles.linkButton}
              onClick={() => navigate('/forgot-password')}
              data-testid='forgot-password-link'
            >
              Forgot your password?
            </button>
          </p>
        </div>
      </div>

      <div className={styles.features}>
        {featuresTitle && <h2 className={styles.featuresTitle}>{featuresTitle}</h2>}
        {featuresSubtitle && (
          <p className={styles.featuresSubtitle}>{featuresSubtitle}</p>
        )}
        <div className={styles.featuresList}>
          {features.map(
            (feature: {
              icon: string;
              iconLabel: string;
              heading: string;
              description: string;
            }) => (
              <div className={styles.feature} key={feature.heading}>
                <FeatureIcon icon={feature.icon} label={feature.iconLabel} />
                <h3 className={styles.featureTitle}>{feature.heading}</h3>
                <p className={styles.featureDesc}>{feature.description}</p>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
};
