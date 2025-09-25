import React from 'react';
import classNames from 'classnames';
import styles from './Button.module.scss';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      type = 'button',
      isLoading = false,
      leftIcon,
      rightIcon,
      fullWidth = false,
      children,
      className,
      disabled,
      ...props
    },
    ref
  ) => {
    const buttonClass = classNames(
      styles.button,
      styles[variant],
      styles[size],
      {
        [styles.loading]: isLoading,
        [styles.fullWidth]: fullWidth,
      },
      className
    );

    // Check if this is an icon-only button (has icons but no text content)
    const isIconOnly = (leftIcon || rightIcon) && !children;
    const needsAriaLabel =
      isIconOnly && !props['aria-label'] && !props['aria-labelledby'];

    // Dev warning for accessibility
    if (import.meta.env.DEV && needsAriaLabel) {
      console.warn(
        'Button: Icon-only buttons should have an aria-label for accessibility. ' +
          'Consider adding an aria-label prop to describe the button action.'
      );
    }

    return (
      <button
        ref={ref}
        type={type}
        className={buttonClass}
        disabled={disabled || isLoading}
        aria-label={needsAriaLabel ? 'Action button' : props['aria-label']}
        {...props}
      >
        {isLoading && <div className={styles.spinner} />}
        {leftIcon && !isLoading && <span className={styles.leftIcon}>{leftIcon}</span>}
        {children}
        {rightIcon && !isLoading && (
          <span className={styles.rightIcon}>{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
