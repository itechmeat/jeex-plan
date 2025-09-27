import classNames from 'classnames';
import React, { useId } from 'react';
import styles from './Textarea.module.css';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
  resize?: 'none' | 'vertical' | 'horizontal' | 'both';
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      error,
      helperText,
      fullWidth = false,
      resize = 'vertical',
      className,
      id,
      rows = 4,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const textareaId = id || generatedId;
    const hasError = Boolean(error);

    const wrapperClass = classNames(styles.wrapper, {
      [styles.fullWidth]: fullWidth,
      [styles.hasError]: hasError,
    });

    const textareaClass = classNames(
      styles.textarea,
      styles[`resize-${resize}`],
      className
    );

    return (
      <div className={wrapperClass}>
        {label && (
          <label htmlFor={textareaId} className={styles.label}>
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          className={textareaClass}
          {...props}
        />
        {(error || helperText) && (
          <div className={styles.helperContainer}>
            {error && (
              <span className={styles.error} role='alert'>
                {error}
              </span>
            )}
            {helperText && !error && (
              <span className={styles.helperText}>{helperText}</span>
            )}
          </div>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
