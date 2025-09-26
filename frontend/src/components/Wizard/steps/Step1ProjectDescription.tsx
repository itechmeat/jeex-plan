import React, { useEffect, useState, useCallback } from 'react';
import { WizardStepProps } from '../Wizard';
import { Input } from '../../ui/Input/Input';
import { Textarea } from '../../ui/Textarea/Textarea';
import { WizardStep1Data, isWizardStep1Data } from '../../../types/api';
import { PROJECT_TYPES, TARGET_AUDIENCES } from '../../../config/wizardOptions';
import styles from './WizardSteps.module.scss';

export const Step1ProjectDescription: React.FC<WizardStepProps> = ({
  data,
  onDataChange,
  onValidationChange,
}) => {
  const [formData, setFormData] = useState<WizardStep1Data>(() => {
    if (isWizardStep1Data(data)) {
      return {
        projectName: data.projectName || '',
        projectDescription: data.projectDescription || '',
        projectType: data.projectType || '',
        targetAudience: data.targetAudience || '',
      };
    }
    return {
      projectName: '',
      projectDescription: '',
      projectType: '',
      targetAudience: '',
    };
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!formData.projectName.trim()) {
      newErrors.projectName = 'Project name is required';
    } else if (formData.projectName.trim().length < 3) {
      newErrors.projectName = 'Project name must be at least 3 characters';
    }

    if (!formData.projectDescription.trim()) {
      newErrors.projectDescription = 'Project description is required';
    } else if (formData.projectDescription.trim().length < 50) {
      newErrors.projectDescription =
        'Project description must be at least 50 characters';
    }

    if (!formData.projectType) {
      newErrors.projectType = 'Project type is required';
    }

    if (!formData.targetAudience) {
      newErrors.targetAudience = 'Target audience is required';
    }

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange(isValid);
    return isValid;
  }, [formData, onValidationChange]);

  const handleFieldChange = (field: keyof WizardStep1Data, value: string) => {
    const newFormData = {
      ...formData,
      [field]: value,
    };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  // Sync with incoming data changes (e.g., when navigating back to this step)
  useEffect(() => {
    if (isWizardStep1Data(data)) {
      const normalizedData = {
        projectName: data.projectName || '',
        projectDescription: data.projectDescription || '',
        projectType: data.projectType || '',
        targetAudience: data.targetAudience || '',
      };

      // Only update if the data has actually changed
      const hasChanged = Object.keys(normalizedData).some(
        key =>
          normalizedData[key as keyof WizardStep1Data] !==
          formData[key as keyof WizardStep1Data]
      );

      if (hasChanged) {
        setFormData(normalizedData);
        onDataChange(normalizedData);
      }
    }
  }, [data, formData, onDataChange]);

  useEffect(() => {
    validateForm();
  }, [formData, validateForm]);

  return (
    <div className={styles.stepContainer}>
      <div className={styles.fieldsGrid}>
        <Input
          label="Project Name"
          placeholder="Enter your project name"
          value={formData.projectName}
          onChange={e => handleFieldChange('projectName', e.target.value)}
          error={errors.projectName}
          fullWidth
        />

        <Textarea
          label="Project Description"
          placeholder="Describe your project in detail. What does it do? What problem does it solve? What are the main features?"
          value={formData.projectDescription}
          onChange={e => handleFieldChange('projectDescription', e.target.value)}
          error={errors.projectDescription}
          rows={6}
          fullWidth
          helperText={`${formData.projectDescription.length}/50 minimum characters`}
        />

        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Project Type</label>
          <div className={styles.optionGrid}>
            {PROJECT_TYPES.map(type => (
              <label key={type} className={styles.optionItem}>
                <input
                  type="radio"
                  name="projectType"
                  value={type}
                  checked={formData.projectType === type}
                  onChange={e => handleFieldChange('projectType', e.target.value)}
                />
                <span className={styles.optionLabel}>{type}</span>
              </label>
            ))}
          </div>
          {errors.projectType && (
            <span className={styles.error} role="alert">
              {errors.projectType}
            </span>
          )}
        </div>

        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Target Audience</label>
          <div className={styles.optionGrid}>
            {TARGET_AUDIENCES.map(audience => (
              <label key={audience} className={styles.optionItem}>
                <input
                  type="radio"
                  name="targetAudience"
                  value={audience}
                  checked={formData.targetAudience === audience}
                  onChange={e => handleFieldChange('targetAudience', e.target.value)}
                />
                <span className={styles.optionLabel}>{audience}</span>
              </label>
            ))}
          </div>
          {errors.targetAudience && (
            <span className={styles.error} role="alert">
              {errors.targetAudience}
            </span>
          )}
        </div>
      </div>

      <div className={styles.summary}>
        <h3>Summary</h3>
        {formData.projectName && (
          <p>
            <strong>Project:</strong> {formData.projectName}
          </p>
        )}
        {formData.projectType && (
          <p>
            <strong>Type:</strong> {formData.projectType}
          </p>
        )}
        {formData.targetAudience && (
          <p>
            <strong>Audience:</strong> {formData.targetAudience}
          </p>
        )}
      </div>
    </div>
  );
};
