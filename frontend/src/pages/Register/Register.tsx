import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button/Button';
import { Input } from '../../components/ui/Input/Input';
import { useAuth } from '../../contexts/useAuth';
import { useLoginFeaturesConfig } from '../../contexts/useLoginFeatures';
import styles from './Register.module.css';

type FeatureIconProps = {
  icon: string;
  label: string;
};

const FeatureIcon: React.FC<FeatureIconProps> = ({ icon, label }) => (
  <span className={styles.featureIcon} role='img' aria-label={label}>
    {icon}
  </span>
);

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register, error: authError, clearError, isLoading: authLoading } = useAuth();
  const {
    title: featuresTitle,
    subtitle: featuresSubtitle,
    features,
  } = useLoginFeaturesConfig();

  const [formData, setFormData] = useState({
    email: '',
    firstName: '',
    lastName: '',
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isLoading = authLoading || isSubmitting;

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

    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required';
    } else if (formData.firstName.trim().length < 2) {
      newErrors.firstName = 'First name must be at least 2 characters';
    }

    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    } else if (formData.lastName.trim().length < 2) {
      newErrors.lastName = 'Last name must be at least 2 characters';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
      newErrors.password =
        'Password must contain at least one uppercase letter, one lowercase letter, and one number';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
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

    if (isSubmitting || isLoading) {
      return;
    }

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await register({
        email: formData.email.trim(),
        firstName: formData.firstName.trim(),
        lastName: formData.lastName.trim(),
        password: formData.password,
        confirmPassword: formData.confirmPassword,
      });
    } catch {
      // Error is handled by AuthContext
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Enter key submission
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isLoading) {
      e.preventDefault();
      const form = e.currentTarget.closest('form');
      if (form) {
        form.requestSubmit();
      }
    }
  };

  return (
    <div className={styles.registerContainer}>
      <div className={styles.registerCard}>
        <div className={styles.header}>
          <h1 className={styles.title}>Join JEEX Plan</h1>
          <p className={styles.subtitle}>Create your account to get started</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className={styles.form}
          noValidate
          data-testid='register-form'
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

          <div className={styles.nameFields}>
            <Input
              label='First Name'
              type='text'
              value={formData.firstName}
              onChange={handleInputChange('firstName')}
              error={errors.firstName}
              placeholder='First name'
              autoComplete='given-name'
              fullWidth
              data-testid='first-name-input'
              disabled={isLoading}
              onKeyDown={handleKeyDown}
            />

            <Input
              label='Last Name'
              type='text'
              value={formData.lastName}
              onChange={handleInputChange('lastName')}
              error={errors.lastName}
              placeholder='Last name'
              autoComplete='family-name'
              fullWidth
              data-testid='last-name-input'
              disabled={isLoading}
              onKeyDown={handleKeyDown}
            />
          </div>

          <Input
            label='Password'
            type='password'
            value={formData.password}
            onChange={handleInputChange('password')}
            error={errors.password}
            placeholder='Create a strong password'
            autoComplete='new-password'
            fullWidth
            data-testid='password-input'
            disabled={isLoading}
            onKeyDown={handleKeyDown}
          />

          <Input
            label='Confirm Password'
            type='password'
            value={formData.confirmPassword}
            onChange={handleInputChange('confirmPassword')}
            error={errors.confirmPassword}
            placeholder='Confirm your password'
            autoComplete='new-password'
            fullWidth
            data-testid='confirm-password-input'
            disabled={isLoading}
            onKeyDown={handleKeyDown}
          />

          <Button
            type='submit'
            variant='primary'
            size='lg'
            isLoading={isLoading}
            disabled={isLoading || isSubmitting}
            fullWidth
            data-testid='sign-up-button'
            onClick={e => {
              if (isLoading || isSubmitting) {
                e.preventDefault();
                return;
              }
            }}
          >
            {isLoading ? 'Creating Account...' : 'Create Account'}
          </Button>
        </form>

        <div className={styles.footer}>
          <p className={styles.footerText}>
            Already have an account?{' '}
            <button
              type='button'
              className={styles.linkButton}
              onClick={() => navigate('/login')}
              data-testid='login-link'
            >
              Sign in here
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
