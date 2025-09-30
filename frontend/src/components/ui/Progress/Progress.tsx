import * as ProgressPrimitive from '@radix-ui/react-progress';
import classNames from 'classnames';
import React, { useEffect, useState } from 'react';
import { PROGRESS_ANIMATION_DURATION } from '../../../constants/animations';
import styles from './Progress.module.css';

export interface ProgressProps
  extends React.ComponentProps<typeof ProgressPrimitive.Root> {
  value: number;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'success' | 'warning' | 'error';
  showValue?: boolean;
  label?: string;
}

export const Progress = React.forwardRef<
  React.ComponentRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(
  (
    {
      value,
      size = 'md',
      variant = 'default',
      showValue = false,
      label,
      className,
      ...props
    },
    ref
  ) => {
    const clampedValue = Math.min(100, Math.max(0, value));
    const progressScale = clampedValue / 100;
    const [isAnimating, setIsAnimating] = useState(false);

    const rootClass = classNames(styles.root, styles[size], styles[variant], className);

    useEffect(() => {
      setIsAnimating(true);
      const timer = setTimeout(() => {
        setIsAnimating(false);
      }, PROGRESS_ANIMATION_DURATION);

      return () => clearTimeout(timer);
    }, [progressScale]);

    return (
      <div className={styles.wrapper}>
        {(label || showValue) && (
          <div className={styles.header}>
            {label && <span className={styles.label}>{label}</span>}
            {showValue && (
              <span className={styles.value}>{Math.round(clampedValue)}%</span>
            )}
          </div>
        )}
        <ProgressPrimitive.Root
          ref={ref}
          className={rootClass}
          value={clampedValue}
          style={{ ['--progress' as string]: progressScale }}
          {...props}
        >
          <ProgressPrimitive.Indicator
            className={classNames(styles.indicator, isAnimating && styles.animating)}
          />
        </ProgressPrimitive.Root>
      </div>
    );
  }
);

Progress.displayName = 'Progress';
