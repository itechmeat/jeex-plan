import React, { useEffect, useState, useCallback } from 'react';
import { WizardStepProps } from '../Wizard';
import { Input } from '../../ui/Input/Input';
import {
  PlanningConfiguration,
  DevelopmentMethodology,
  TimeUnit,
  isPlanningConfiguration,
  isTimelinePreferences,
} from '../../../types/api';
import styles from './WizardSteps.module.scss';

const methodologies = [
  {
    methodology: DevelopmentMethodology.AGILE,
    name: 'Agile',
    description: 'Iterative development with sprints, scrums, and continuous delivery',
  },
  {
    methodology: DevelopmentMethodology.WATERFALL,
    name: 'Waterfall',
    description: 'Sequential development phases with detailed upfront planning',
  },
  {
    methodology: DevelopmentMethodology.HYBRID,
    name: 'Hybrid',
    description: 'Combines agile and waterfall approaches based on project needs',
  },
];

const developmentPhases = [
  {
    id: 'requirements',
    name: 'Requirements Analysis',
    description: 'Gather and document project requirements',
  },
  {
    id: 'design',
    name: 'System Design',
    description: 'Create system architecture and UI/UX designs',
  },
  {
    id: 'development',
    name: 'Development',
    description: 'Implement features and functionality',
  },
  { id: 'testing', name: 'Testing', description: 'Quality assurance and bug fixing' },
  {
    id: 'deployment',
    name: 'Deployment',
    description: 'Release to production environment',
  },
  {
    id: 'maintenance',
    name: 'Maintenance',
    description: 'Ongoing support and updates',
  },
];

const deliverableTypes = [
  {
    id: 'technical-spec',
    name: 'Technical Specification',
    description: 'Detailed technical requirements and architecture',
  },
  {
    id: 'api-docs',
    name: 'API Documentation',
    description: 'RESTful API endpoints and schemas',
  },
  {
    id: 'user-guide',
    name: 'User Guide',
    description: 'End-user documentation and tutorials',
  },
  {
    id: 'deployment-guide',
    name: 'Deployment Guide',
    description: 'Installation and configuration instructions',
  },
  {
    id: 'testing-plan',
    name: 'Testing Plan',
    description: 'Test cases and quality assurance procedures',
  },
  {
    id: 'project-plan',
    name: 'Project Plan',
    description: 'Timeline, milestones, and resource allocation',
  },
];

const timeUnits = [
  { unit: TimeUnit.WEEKS, name: 'Weeks', description: 'Short-term projects' },
  { unit: TimeUnit.MONTHS, name: 'Months', description: 'Medium-term projects' },
  { unit: TimeUnit.QUARTERS, name: 'Quarters', description: 'Long-term projects' },
];

export const Step3PlanningConfiguration: React.FC<WizardStepProps> = ({
  data,
  onDataChange,
  onValidationChange,
}) => {
  const [formData, setFormData] = useState<PlanningConfiguration>(() => {
    if (isPlanningConfiguration(data)) {
      const timeline = isTimelinePreferences(data.timeline)
        ? data.timeline
        : {
            duration: 3,
            unit: TimeUnit.MONTHS,
            milestones: ['MVP', 'Beta Release', 'Production Launch'],
          };
      return {
        methodology: data.methodology || DevelopmentMethodology.AGILE,
        phases: data.phases || ['requirements', 'design', 'development', 'testing'],
        deliverables: data.deliverables || ['technical-spec', 'api-docs'],
        timeline,
      };
    }
    return {
      methodology: DevelopmentMethodology.AGILE,
      phases: ['requirements', 'design', 'development', 'testing'],
      deliverables: ['technical-spec', 'api-docs'],
      timeline: {
        duration: 3,
        unit: TimeUnit.MONTHS,
        milestones: ['MVP', 'Beta Release', 'Production Launch'],
      },
    };
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!formData.methodology) {
      newErrors.methodology = 'Development methodology is required';
    }

    if (formData.phases.length === 0) {
      newErrors.phases = 'At least one development phase is required';
    }

    if (formData.deliverables.length === 0) {
      newErrors.deliverables = 'At least one deliverable type is required';
    }

    if (!formData.timeline.duration || formData.timeline.duration < 1) {
      newErrors.duration = 'Project duration must be at least 1';
    }

    if (!formData.timeline.unit) {
      newErrors.unit = 'Time unit is required';
    }

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange(isValid);
    return isValid;
  }, [formData, onValidationChange]);

  const handleMethodologyChange = (methodology: DevelopmentMethodology) => {
    const newFormData = { ...formData, methodology };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handlePhaseToggle = (phaseId: string) => {
    const phases = formData.phases.includes(phaseId)
      ? formData.phases.filter(p => p !== phaseId)
      : [...formData.phases, phaseId];

    const newFormData = { ...formData, phases };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleDeliverableToggle = (deliverableId: string) => {
    const deliverables = formData.deliverables.includes(deliverableId)
      ? formData.deliverables.filter(d => d !== deliverableId)
      : [...formData.deliverables, deliverableId];

    const newFormData = { ...formData, deliverables };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleTimelineChange = (
    field: keyof typeof formData.timeline,
    value: string | number | string[]
  ) => {
    const timeline = { ...formData.timeline, [field]: value };
    const newFormData = { ...formData, timeline };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleMilestoneChange = (index: number, value: string) => {
    const milestones = [...formData.timeline.milestones];
    milestones[index] = value;
    handleTimelineChange('milestones', milestones);
  };

  const addMilestone = () => {
    const milestones = [...formData.timeline.milestones, ''];
    handleTimelineChange('milestones', milestones);
  };

  const removeMilestone = (index: number) => {
    const milestones = formData.timeline.milestones.filter((_, i) => i !== index);
    handleTimelineChange('milestones', milestones);
  };

  useEffect(() => {
    validateForm();
  }, [formData, validateForm]);

  return (
    <div className={styles.stepContainer}>
      <div className={styles.fieldsGrid}>
        {/* Development Methodology */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Development Methodology</label>
          <div className={styles.optionGrid}>
            {methodologies.map(({ methodology, name, description }) => (
              <label key={methodology} className={styles.optionItem}>
                <input
                  type="radio"
                  name="methodology"
                  value={methodology}
                  checked={formData.methodology === methodology}
                  onChange={() => handleMethodologyChange(methodology)}
                />
                <div className={styles.optionContent}>
                  <div className={styles.optionLabel}>{name}</div>
                  <div className={styles.optionDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.methodology && (
            <span className={styles.error} role="alert">
              {errors.methodology}
            </span>
          )}
        </div>

        {/* Development Phases */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Development Phases</label>
          <p className={styles.selectDescription}>
            Choose phases to include in your project
          </p>
          <div className={styles.checkboxGroup}>
            {developmentPhases.map(({ id, name, description }) => (
              <label key={id} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={formData.phases.includes(id)}
                  onChange={() => handlePhaseToggle(id)}
                />
                <div className={styles.checkboxContent}>
                  <div className={styles.checkboxLabel}>{name}</div>
                  <div className={styles.checkboxDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.phases && (
            <span className={styles.error} role="alert">
              {errors.phases}
            </span>
          )}
        </div>

        {/* Deliverables */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Project Deliverables</label>
          <p className={styles.selectDescription}>
            Select documentation and deliverables to generate
          </p>
          <div className={styles.checkboxGroup}>
            {deliverableTypes.map(({ id, name, description }) => (
              <label key={id} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={formData.deliverables.includes(id)}
                  onChange={() => handleDeliverableToggle(id)}
                />
                <div className={styles.checkboxContent}>
                  <div className={styles.checkboxLabel}>{name}</div>
                  <div className={styles.checkboxDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.deliverables && (
            <span className={styles.error} role="alert">
              {errors.deliverables}
            </span>
          )}
        </div>

        {/* Timeline Configuration */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Project Timeline</label>
          <div className={styles.inputGroup}>
            <Input
              label="Duration"
              type="number"
              min="1"
              value={formData.timeline.duration.toString()}
              onChange={e =>
                handleTimelineChange('duration', parseInt(e.target.value) || 0)
              }
              error={errors.duration}
            />
            <div className={styles.selectGroup}>
              <label className={styles.selectLabel}>Time Unit</label>
              <div className={styles.optionGrid}>
                {timeUnits.map(({ unit, name, description }) => (
                  <label key={unit} className={styles.optionItem}>
                    <input
                      type="radio"
                      name="timeUnit"
                      value={unit}
                      checked={formData.timeline.unit === unit}
                      onChange={() => handleTimelineChange('unit', unit)}
                    />
                    <div className={styles.optionContent}>
                      <div className={styles.optionLabel}>{name}</div>
                      <div className={styles.optionDescription}>{description}</div>
                    </div>
                  </label>
                ))}
              </div>
              {errors.unit && (
                <span className={styles.error} role="alert">
                  {errors.unit}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Milestones */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Project Milestones</label>
          <p className={styles.selectDescription}>
            Define key milestones for your project
          </p>
          <div className={styles.milestonesContainer}>
            {formData.timeline.milestones.map((milestone, index) => (
              <div key={index} className={styles.milestoneItem}>
                <Input
                  placeholder={`Milestone ${index + 1}`}
                  value={milestone}
                  onChange={e => handleMilestoneChange(index, e.target.value)}
                  fullWidth
                />
                {formData.timeline.milestones.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeMilestone(index)}
                    className={styles.removeMilestone}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
            <button
              type="button"
              onClick={addMilestone}
              className={styles.addMilestone}
            >
              + Add Milestone
            </button>
          </div>
        </div>
      </div>

      <div className={styles.summary}>
        <h3>Planning Summary</h3>
        <p>
          <strong>Methodology:</strong>{' '}
          {methodologies.find(m => m.methodology === formData.methodology)?.name}
        </p>
        <p>
          <strong>Phases:</strong> {formData.phases.length} selected
        </p>
        <p>
          <strong>Deliverables:</strong> {formData.deliverables.length} types
        </p>
        <p>
          <strong>Timeline:</strong> {formData.timeline.duration}{' '}
          {formData.timeline.unit}
        </p>
        <p>
          <strong>Milestones:</strong> {formData.timeline.milestones.length} defined
        </p>
      </div>
    </div>
  );
};
