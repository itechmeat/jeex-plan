import classNames from 'classnames';
import React, { useCallback, useState } from 'react';
import { Button } from '../ui/Button/Button';
import { Progress } from '../ui/Progress/Progress';
import styles from './Wizard.module.css';

export interface WizardStep {
  id: string;
  title: string;
  description?: string;
  component: React.ComponentType<WizardStepProps>;
  isValid?: boolean;
}

export interface WizardStepProps {
  data: Record<string, unknown>;
  onDataChange: (data: Record<string, unknown>) => void;
  onValidationChange: (isValid: boolean) => void;
}

export interface WizardProps {
  steps: WizardStep[];
  onComplete: (data: Record<string, unknown>) => void;
  onCancel?: () => void;
  initialData?: Record<string, unknown>;
  className?: string;
}

export const Wizard: React.FC<WizardProps> = ({
  steps,
  onComplete,
  onCancel,
  initialData = {},
  className,
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [wizardData, setWizardData] = useState(initialData);
  const [stepValidation, setStepValidation] = useState<Record<string, boolean>>({});

  const handleDataChange = useCallback(
    (stepId: string, data: Record<string, unknown>) => {
      setWizardData((prev: Record<string, unknown>) => ({
        ...prev,
        [stepId]: data,
      }));
    },
    []
  );

  const handleValidationChange = useCallback((stepId: string, isValid: boolean) => {
    setStepValidation(prev => ({
      ...prev,
      [stepId]: isValid,
    }));
  }, []);

  // Handle empty steps array gracefully
  if (!steps || steps.length === 0) {
    return (
      <div className={classNames(styles.wizard, styles.empty, className)}>
        <div className={styles.emptyMessage}>No steps available</div>
      </div>
    );
  }

  const currentStep = steps[currentStepIndex];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === steps.length - 1;
  const progress = ((currentStepIndex + 1) / steps.length) * 100;

  const isCurrentStepValid = () => {
    return Boolean(stepValidation[currentStep.id] ?? currentStep.isValid ?? false);
  };

  const goToNextStep = () => {
    if (isCurrentStepValid() && !isLastStep) {
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const goToPreviousStep = () => {
    if (!isFirstStep) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const goToStep = (index: number) => {
    if (index >= 0 && index < steps.length) {
      setCurrentStepIndex(index);
    }
  };

  const handleComplete = () => {
    if (isCurrentStepValid()) {
      onComplete(wizardData);
    }
  };

  const StepComponent = currentStep.component;

  return (
    <div className={classNames(styles.wizard, className)}>
      {/* Progress Header */}
      <div className={styles.header}>
        <div className={styles.progressSection}>
          <Progress
            value={progress}
            size='md'
            label={`Step ${currentStepIndex + 1} of ${steps.length}`}
            showValue={false}
          />
        </div>

        {/* Step Navigation */}
        <div className={styles.stepNav}>
          {steps.map((step, index) => (
            <button
              key={step.id}
              type='button'
              className={classNames(styles.stepNavItem, {
                [styles.active]: index === currentStepIndex,
                [styles.completed]: index < currentStepIndex,
                [styles.clickable]: index < currentStepIndex,
              })}
              aria-current={index === currentStepIndex ? 'step' : undefined}
              disabled={index >= currentStepIndex}
              onClick={() => index < currentStepIndex && goToStep(index)}
            >
              <div className={styles.stepNumber}>
                {index < currentStepIndex ? '✓' : index + 1}
              </div>
              <div className={styles.stepInfo}>
                <div className={styles.stepTitle}>{step.title}</div>
                {step.description && (
                  <div className={styles.stepDescription}>{step.description}</div>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Current Step Content */}
      <div className={styles.content}>
        <div className={styles.stepHeader}>
          <h2 className={styles.stepTitle}>{currentStep.title}</h2>
          {currentStep.description && (
            <p className={styles.stepDescription}>{currentStep.description}</p>
          )}
        </div>

        <div className={styles.stepContent}>
          <StepComponent
            data={
              (wizardData[currentStep.id] as Record<string, unknown>) ||
              ({} as Record<string, unknown>)
            }
            onDataChange={data => handleDataChange(currentStep.id, data)}
            onValidationChange={isValid =>
              handleValidationChange(currentStep.id, isValid)
            }
          />
        </div>
      </div>

      {/* Navigation Footer */}
      <div className={styles.footer}>
        <div className={styles.navigationButtons}>
          {onCancel && (
            <Button variant='ghost' onClick={onCancel}>
              Cancel
            </Button>
          )}

          <div className={styles.rightButtons}>
            {!isFirstStep && (
              <Button variant='outline' onClick={goToPreviousStep}>
                Previous
              </Button>
            )}

            {!isLastStep && (
              <Button
                variant='primary'
                onClick={goToNextStep}
                disabled={!isCurrentStepValid()}
              >
                Next
              </Button>
            )}

            {isLastStep && (
              <Button
                variant='primary'
                onClick={handleComplete}
                disabled={!isCurrentStepValid()}
              >
                Complete
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
