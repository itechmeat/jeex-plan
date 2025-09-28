import classNames from 'classnames';
import React from 'react';
import styles from './Input.module.css';

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
      id,
      ...restProps
    },
    ref
  ) => {
    const generatedId = React.useId();
    const inputId = id ?? generatedId;
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

    const { ['aria-describedby']: ariaDescribedByProp, ...inputProps } = restProps;

    // Build aria-describedby based on what helper elements exist and consumer-provided descriptors
    const ariaDescribedBy = React.useMemo(() => {
      const ids = new Set<string>();

      if (ariaDescribedByProp) {
        ariaDescribedByProp
          .toString()
          .split(/\s+/)
          .filter(Boolean)
          .forEach(token => ids.add(token));
      }

      if (error) {
        ids.add(errorId);
      }

      if (helperText) {
        ids.add(helperId);
      }

      return ids.size > 0 ? Array.from(ids).join(' ') : undefined;
    }, [ariaDescribedByProp, error, helperText, errorId, helperId]);

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
            {...inputProps}
            aria-describedby={ariaDescribedBy}
            aria-invalid={hasError || undefined}
            aria-errormessage={hasError ? errorId : undefined}
          />
          {rightIcon && <div className={styles.rightIcon}>{rightIcon}</div>}
        </div>
        {(error || helperText) && (
          <div className={styles.helperContainer}>
            {error && (
              <span id={errorId} className={styles.error} role='alert'>
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
