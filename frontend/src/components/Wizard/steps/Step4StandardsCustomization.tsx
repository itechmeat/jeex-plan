import React, { useEffect, useState, useCallback } from 'react';
import { WizardStepProps } from '../Wizard';
import {
  StandardsCustomization,
  DocumentationFormat,
  isStandardsCustomization,
} from '../../../types/api';
import styles from './WizardSteps.module.scss';

const codingStandardsOptions = [
  { id: 'eslint', name: 'ESLint', description: 'JavaScript/TypeScript linting rules' },
  {
    id: 'prettier',
    name: 'Prettier',
    description: 'Code formatting and style consistency',
  },
  {
    id: 'sonarqube',
    name: 'SonarQube',
    description: 'Code quality and security analysis',
  },
  { id: 'pep8', name: 'PEP 8', description: 'Python style guide' },
  {
    id: 'google-style',
    name: 'Google Style Guides',
    description: 'Language-specific style guides',
  },
  {
    id: 'airbnb-style',
    name: 'Airbnb Style Guide',
    description: 'JavaScript style guide',
  },
  {
    id: 'clean-code',
    name: 'Clean Code Principles',
    description: "Robert Martin's clean code practices",
  },
  {
    id: 'solid-principles',
    name: 'SOLID Principles',
    description: 'Object-oriented design principles',
  },
];

const documentationFormats = [
  {
    format: DocumentationFormat.MARKDOWN,
    name: 'Markdown',
    description: 'Standard Markdown format (.md files)',
  },
  {
    format: DocumentationFormat.CONFLUENCE,
    name: 'Confluence',
    description: 'Atlassian Confluence wiki format',
  },
  {
    format: DocumentationFormat.NOTION,
    name: 'Notion',
    description: 'Notion database and page format',
  },
  {
    format: DocumentationFormat.CUSTOM,
    name: 'Custom Format',
    description: 'Custom documentation template',
  },
];

const reviewProcessOptions = [
  {
    id: 'code-review',
    name: 'Code Review',
    description: 'Peer review of code changes',
  },
  {
    id: 'design-review',
    name: 'Design Review',
    description: 'Architecture and design review',
  },
  {
    id: 'security-review',
    name: 'Security Review',
    description: 'Security assessment and review',
  },
  {
    id: 'performance-review',
    name: 'Performance Review',
    description: 'Performance analysis and optimization',
  },
  {
    id: 'documentation-review',
    name: 'Documentation Review',
    description: 'Review of technical documentation',
  },
  {
    id: 'automated-testing',
    name: 'Automated Testing',
    description: 'Unit, integration, and E2E tests',
  },
];

const qualityGateOptions = [
  {
    id: 'unit-tests',
    name: 'Unit Tests',
    description: 'Minimum test coverage requirements',
  },
  {
    id: 'integration-tests',
    name: 'Integration Tests',
    description: 'API and service integration tests',
  },
  { id: 'e2e-tests', name: 'E2E Tests', description: 'End-to-end user journey tests' },
  {
    id: 'code-coverage',
    name: 'Code Coverage',
    description: 'Minimum code coverage thresholds',
  },
  {
    id: 'performance-benchmarks',
    name: 'Performance Benchmarks',
    description: 'Response time and throughput requirements',
  },
  {
    id: 'security-scans',
    name: 'Security Scans',
    description: 'Vulnerability and security assessments',
  },
  {
    id: 'accessibility-tests',
    name: 'Accessibility Tests',
    description: 'WCAG compliance and accessibility',
  },
  {
    id: 'browser-compatibility',
    name: 'Browser Compatibility',
    description: 'Cross-browser testing requirements',
  },
];

export const Step4StandardsCustomization: React.FC<WizardStepProps> = ({
  data,
  onDataChange,
  onValidationChange,
}) => {
  const [formData, setFormData] = useState<StandardsCustomization>(() => {
    if (isStandardsCustomization(data)) {
      return {
        codingStandards: data.codingStandards || ['eslint', 'prettier', 'clean-code'],
        documentationFormat: data.documentationFormat || DocumentationFormat.MARKDOWN,
        reviewProcesses: data.reviewProcesses || ['code-review', 'automated-testing'],
        qualityGates: data.qualityGates || ['unit-tests', 'code-coverage'],
      };
    }
    return {
      codingStandards: ['eslint', 'prettier', 'clean-code'],
      documentationFormat: DocumentationFormat.MARKDOWN,
      reviewProcesses: ['code-review', 'automated-testing'],
      qualityGates: ['unit-tests', 'code-coverage'],
    };
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = useCallback(() => {
    const newErrors: Record<string, string> = {};

    if (formData.codingStandards.length === 0) {
      newErrors.codingStandards = 'At least one coding standard is required';
    }

    if (!formData.documentationFormat) {
      newErrors.documentationFormat = 'Documentation format is required';
    }

    if (formData.reviewProcesses.length === 0) {
      newErrors.reviewProcesses = 'At least one review process is required';
    }

    if (formData.qualityGates.length === 0) {
      newErrors.qualityGates = 'At least one quality gate is required';
    }

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    onValidationChange(isValid);
    return isValid;
  }, [formData, onValidationChange]);

  const handleCodingStandardToggle = (standardId: string) => {
    const codingStandards = formData.codingStandards.includes(standardId)
      ? formData.codingStandards.filter(s => s !== standardId)
      : [...formData.codingStandards, standardId];

    const newFormData = { ...formData, codingStandards };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleDocumentationFormatChange = (format: DocumentationFormat) => {
    const newFormData = { ...formData, documentationFormat: format };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleReviewProcessToggle = (processId: string) => {
    const reviewProcesses = formData.reviewProcesses.includes(processId)
      ? formData.reviewProcesses.filter(p => p !== processId)
      : [...formData.reviewProcesses, processId];

    const newFormData = { ...formData, reviewProcesses };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  const handleQualityGateToggle = (gateId: string) => {
    const qualityGates = formData.qualityGates.includes(gateId)
      ? formData.qualityGates.filter(g => g !== gateId)
      : [...formData.qualityGates, gateId];

    const newFormData = { ...formData, qualityGates };
    setFormData(newFormData);
    onDataChange(newFormData);
  };

  useEffect(() => {
    validateForm();
  }, [formData, validateForm]);

  return (
    <div className={styles.stepContainer}>
      <div className={styles.fieldsGrid}>
        {/* Coding Standards */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Coding Standards</label>
          <p className={styles.selectDescription}>
            Choose coding standards and guidelines to enforce
          </p>
          <div className={styles.checkboxGroup}>
            {codingStandardsOptions.map(({ id, name, description }) => (
              <label key={id} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={formData.codingStandards.includes(id)}
                  onChange={() => handleCodingStandardToggle(id)}
                />
                <div className={styles.checkboxContent}>
                  <div className={styles.checkboxLabel}>{name}</div>
                  <div className={styles.checkboxDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.codingStandards && (
            <span className={styles.error} role="alert">
              {errors.codingStandards}
            </span>
          )}
        </div>

        {/* Documentation Format */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Documentation Format</label>
          <p className={styles.selectDescription}>
            Select the primary format for generated documentation
          </p>
          <div className={styles.optionGrid}>
            {documentationFormats.map(({ format, name, description }) => (
              <label key={format} className={styles.optionItem}>
                <input
                  type="radio"
                  name="documentationFormat"
                  value={format}
                  checked={formData.documentationFormat === format}
                  onChange={() => handleDocumentationFormatChange(format)}
                />
                <div className={styles.optionContent}>
                  <div className={styles.optionLabel}>{name}</div>
                  <div className={styles.optionDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.documentationFormat && (
            <span className={styles.error} role="alert">
              {errors.documentationFormat}
            </span>
          )}
        </div>

        {/* Review Processes */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Review Processes</label>
          <p className={styles.selectDescription}>
            Define review processes to include in your workflow
          </p>
          <div className={styles.checkboxGroup}>
            {reviewProcessOptions.map(({ id, name, description }) => (
              <label key={id} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={formData.reviewProcesses.includes(id)}
                  onChange={() => handleReviewProcessToggle(id)}
                />
                <div className={styles.checkboxContent}>
                  <div className={styles.checkboxLabel}>{name}</div>
                  <div className={styles.checkboxDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.reviewProcesses && (
            <span className={styles.error} role="alert">
              {errors.reviewProcesses}
            </span>
          )}
        </div>

        {/* Quality Gates */}
        <div className={styles.selectGroup}>
          <label className={styles.selectLabel}>Quality Gates</label>
          <p className={styles.selectDescription}>
            Set quality gates that must pass before deployment
          </p>
          <div className={styles.checkboxGroup}>
            {qualityGateOptions.map(({ id, name, description }) => (
              <label key={id} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={formData.qualityGates.includes(id)}
                  onChange={() => handleQualityGateToggle(id)}
                />
                <div className={styles.checkboxContent}>
                  <div className={styles.checkboxLabel}>{name}</div>
                  <div className={styles.checkboxDescription}>{description}</div>
                </div>
              </label>
            ))}
          </div>
          {errors.qualityGates && (
            <span className={styles.error} role="alert">
              {errors.qualityGates}
            </span>
          )}
        </div>
      </div>

      <div className={styles.summary}>
        <h3>Standards Summary</h3>
        <p>
          <strong>Coding Standards:</strong> {formData.codingStandards.length} selected
        </p>
        <p>
          <strong>Documentation:</strong>{' '}
          {
            documentationFormats.find(f => f.format === formData.documentationFormat)
              ?.name
          }
        </p>
        <p>
          <strong>Review Processes:</strong> {formData.reviewProcesses.length} defined
        </p>
        <p>
          <strong>Quality Gates:</strong> {formData.qualityGates.length} configured
        </p>
      </div>
    </div>
  );
};
