import React from 'react';
import classNames from 'classnames';
import styles from './Input.module.scss';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      error,
      helperText,
      leftIcon,
      rightIcon,
      fullWidth = false,
      className,
      ...props
    },
    ref
  ) => {
    const inputId = React.useId();
    const errorId = React.useId();
    const helperId = React.useId();
    const hasError = Boolean(error);

    const wrapperClass = classNames(styles.wrapper, {
      [styles.fullWidth]: fullWidth,
      [styles.hasError]: hasError,
      [styles.hasLeftIcon]: Boolean(leftIcon),
      [styles.hasRightIcon]: Boolean(rightIcon),
    });

    const inputClass = classNames(styles.input, className);

    // Build aria-describedby based on what helper elements exist
    const ariaDescribedBy = React.useMemo(() => {
      const ids = [];
      if (error) ids.push(errorId);
      if (helperText) ids.push(helperId);
      return ids.length > 0 ? ids.join(' ') : undefined;
    }, [error, helperText, errorId, helperId]);

    return (
      <div className={wrapperClass}>
        {label && (
          <label htmlFor={inputId} className={styles.label}>
            {label}
          </label>
        )}
        <div className={styles.inputContainer}>
          {leftIcon && <div className={styles.leftIcon}>{leftIcon}</div>}
          <input
            ref={ref}
            id={inputId}
            className={inputClass}
            aria-describedby={ariaDescribedBy}
            {...props}
          />
          {rightIcon && <div className={styles.rightIcon}>{rightIcon}</div>}
        </div>
        {(error || helperText) && (
          <div className={styles.helperContainer}>
            {error && (
              <span id={errorId} className={styles.error} role="alert">
                {error}
              </span>
            )}
            {helperText && !error && (
              <span id={helperId} className={styles.helperText}>
                {helperText}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
