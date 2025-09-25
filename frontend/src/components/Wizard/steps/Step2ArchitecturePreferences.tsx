import React, { useEffect, useState, useCallback } from 'react';
import { WizardStepProps } from '../Wizard';
import {
  ArchitecturePreferences,
  ArchitectureStyle,
  ScalabilityLevel,
  isArchitecturePreferences,
} from '../../../types/api';
import styles from './WizardSteps.module.scss';

const isValidArchitectureStyle = (value: unknown): value is ArchitectureStyle =>
  typeof value === 'string' && Object.values(ArchitectureStyle).includes(value as ArchitectureStyle);

const isValidScalabilityLevel = (value: unknown): value is ScalabilityLevel =>
  typeof value === 'string' && Object.values(ScalabilityLevel).includes(value as ScalabilityLevel);

const toStringArray = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

const architectureStyles = [
  {
    style: ArchitectureStyle.MICROSERVICES,
    name: 'Microservices',
    description: 'Distributed architecture with independent, loosely coupled services',
  },
  {
    style: ArchitectureStyle.MONOLITHIC,
    name: 'Monolithic',
    description: 'Single deployable unit with all components integrated',
  },
  {
    style: ArchitectureStyle.SERVERLESS,
    name: 'Serverless',
    description: 'Function-as-a-Service with automatic scaling and management',
  },
  {
    style: ArchitectureStyle.EVENT_DRIVEN,
    name: 'Event Driven',
    description: 'Architecture based on event production, detection, and consumption',
  },
];

const architecturePatterns = [
  {
    id: 'mvc',
    name: 'MVC (Model-View-Controller)',
    description: 'Separates application logic into three components',
  },
  {
    id: 'mvp',
    name: 'MVP (Model-View-Presenter)',
    description: 'Variant of MVC with presenter handling UI logic',
  },
  {
    id: 'mvvm',
    name: 'MVVM (Model-View-ViewModel)',
    description: 'Binding between view and view model',
  },
  {
    id: 'layered',
    name: 'Layered Architecture',
    description: 'Organized into horizontal layers with dependencies',
  },
  {
    id: 'hexagonal',
    name: 'Hexagonal (Ports & Adapters)',
    description: 'Isolates core logic from external concerns',
  },
  {
    id: 'clean',
    name: 'Clean Architecture',
    description: 'Dependency inversion with concentric layers',
  },
  {
    id: 'cqrs',
    name: 'CQRS (Command Query Responsibility Segregation)',
    description: 'Separate models for reading and writing',
  },
  {
    id: 'event-sourcing',
    name: 'Event Sourcing',
    description: 'Store state changes as events',
  },
];

const technologies = [
  {
    category: 'Frontend',
    items: ['React', 'Vue.js', 'Angular', 'Svelte', 'Next.js', 'Nuxt.js'],
  },
  {
    category: 'Backend',
    items: ['Node.js', 'Python', 'Java', 'C#', 'Go', 'Rust', 'PHP'],
  },
  {
    category: 'Database',
    items: ['PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch', 'SQLite'],
  },
  {
    category: 'Cloud',
    items: ['AWS', 'Azure', 'Google Cloud', 'Vercel', 'Netlify', 'DigitalOcean'],
  },
  {
    category: 'DevOps',
    items: [
      'Docker',
      'Kubernetes',
      'Jenkins',
      'GitHub Actions',
      'Terraform',
      'Ansible',
    ],
  },
];

const scalabilityLevels = [
  {
    level: ScalabilityLevel.SMALL,
    name: 'Small Scale',
    description: 'Up to 1,000 users, simple deployment',
    users: '< 1K users',
  },
  {
    level: ScalabilityLevel.MEDIUM,
    name: 'Medium Scale',
    description: 'Up to 10,000 users, moderate complexity',
    users: '1K - 10K users',
  },
  {
    level: ScalabilityLevel.LARGE,
    name: 'Large Scale',
    description: 'Up to 100,000 users, high availability',
    users: '10K - 100K users',
  },
  {
    level: ScalabilityLevel.ENTERPRISE,
    name: 'Enterprise Scale',
    description: 'Unlimited users, global distribution',
    users: '100K+ users',
  },
];

export const Step2ArchitecturePreferences: React.FC<WizardStepProps> = ({
  data,
  onDataChange,
  onValidationChange,
}) => {
  const [formData, setFormData] = useState<ArchitecturePreferences>(() => {
    if (isArchitecturePreferences(data)) {
      return {
        style: isValidArchitectureStyle(data.style)
          ? data.style
          : ArchitectureStyle.MICROSERVICES,
        patterns: toStringArray(data.patterns),
        technologies: toStringArray(data.technologies),
        scalability: isValidScalabilityLevel(data.scalability)
          ? data.scalability
          : ScalabilityLevel.MEDIUM,
      };
    }
    return {
      style: ArchitectureStyle.MICROSERVICES,
      patterns: [],
      technologies: [],
      scalability: ScalabilityLevel.MEDIUM,
    };
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (!formData.style) {
      newErrors.style = 'Architecture style is required';
    }

    if (formData.patterns.length === 0) {
      newErrors.patterns = 'At least one architecture pattern is required';
    }

    if (formData.technologies.length === 0) {
      newErrors.technologies = 'At least one technology is required';
    }

    if (!formData.scalability) {
      newErrors.scalability = 'Scalability level is required';
    }

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange(isValid);
    return isValid;
  }, [formData, onValidationChange]);

  const handleStyleChange = (style: ArchitectureStyle) => {
    const newFormData = { ...formData, style };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handlePatternToggle = (patternId: string) => {
    const patterns = formData.patterns.includes(patternId)
      ? formData.patterns.filter(p => p !== patternId)
      : [...formData.patterns, patternId];

    const newFormData = { ...formData, patterns };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleTechnologyToggle = (technology: string) => {
    const technologies = formData.technologies.includes(technology)
      ? formData.technologies.filter(t => t !== technology)
      : [...formData.technologies, technology];

    const newFormData = { ...formData, technologies };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleScalabilityChange = (scalability: ScalabilityLevel) => {
    const newFormData = { ...formData, scalability };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  useEffect(() => {
    validateForm();
  }, [formData, validateForm]);

  return (
    <div className={styles.stepContainer}>
      <div className={styles.fieldsGrid}>
        {/* Architecture Style */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Architecture Style</label>
          <div className={styles.optionGrid}>
            {architectureStyles.map(({ style, name, description }) => (
              <label key={style} className={styles.optionItem}>
                <input
                  type="radio"
                  name="architectureStyle"
                  value={style}
                  checked={formData.style === style}
                  onChange={() => handleStyleChange(style)}
                />
                <div className={styles.optionContent}>
                  <div className={styles.optionLabel}>{name}</div>
                  <div className={styles.optionDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.style && (
            <span className={styles.error} role="alert">
              {errors.style}
            </span>
          )}
        </div>

        {/* Architecture Patterns */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Architecture Patterns</label>
          <p className={styles.selectDescription}>
            Choose patterns that fit your project (select multiple)
          </p>
          <div className={styles.checkboxGroup}>
            {architecturePatterns.map(({ id, name, description }) => (
              <label key={id} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={formData.patterns.includes(id)}
                  onChange={() => handlePatternToggle(id)}
                />
                <div className={styles.checkboxContent}>
                  <div className={styles.checkboxLabel}>{name}</div>
                  <div className={styles.checkboxDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.patterns && (
            <span className={styles.error} role="alert">
              {errors.patterns}
            </span>
          )}
        </div>

        {/* Technologies */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Technology Stack</label>
          <p className={styles.selectDescription}>
            Select technologies you want to use
          </p>
          {technologies.map(({ category, items }) => (
            <div key={category}>
              <h4 className={styles.categoryLabel}>{category}</h4>
              <div className={styles.checkboxGroup}>
                {items.map(tech => (
                  <label key={tech} className={styles.checkboxItem}>
                    <input
                      type="checkbox"
                      checked={formData.technologies.includes(tech)}
                      onChange={() => handleTechnologyToggle(tech)}
                    />
                    <div className={styles.checkboxContent}>
                      <div className={styles.checkboxLabel}>{tech}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}
          {errors.technologies && (
            <span className={styles.error} role="alert">
              {errors.technologies}
            </span>
          )}
        </div>

        {/* Scalability Level */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Scalability Requirements</label>
          <div className={styles.optionGrid}>
            {scalabilityLevels.map(({ level, name, description, users }) => (
              <label key={level} className={styles.optionItem}>
                <input
                  type="radio"
                  name="scalability"
                  value={level}
                  checked={formData.scalability === level}
                  onChange={() => handleScalabilityChange(level)}
                />
                <div className={styles.optionContent}>
                  <div className={styles.optionLabel}>{name}</div>
                  <div className={styles.optionDescription}>{description}</div>
                  <div className={styles.optionMeta}>{users}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.scalability && (
            <span className={styles.error} role="alert">
              {errors.scalability}
            </span>
          )}
        </div>
      </div>

      <div className={styles.summary}>
        <h3>Architecture Summary</h3>
        <p>
          <strong>Style:</strong>{' '}
          {architectureStyles.find(s => s.style === formData.style)?.name}
        </p>
        <p>
          <strong>Patterns:</strong> {formData.patterns.length} selected
        </p>
        <p>
          <strong>Technologies:</strong> {formData.technologies.length} selected
        </p>
        <p>
          <strong>Scale:</strong>{' '}
          {scalabilityLevels.find(s => s.level === formData.scalability)?.name}
        </p>
      </div>
    </div>
  );
};
