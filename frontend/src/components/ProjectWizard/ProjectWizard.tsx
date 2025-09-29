import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArchitectureStyle,
  CreateProjectRequest,
  DevelopmentMethodology,
  DocumentationFormat,
  isArchitecturePreferences,
  isPlanningConfiguration,
  isStandardsCustomization,
  isWizardStep1Data,
  ScalabilityLevel,
  TimeUnit,
  WizardData,
} from '../../types/api';
import { ROUTES } from '../../config/routes';
import { handleApiError } from '../../services/api';
import { useCreateProject } from '../../hooks/useProjects';
import { Step1ProjectDescription } from '../Wizard/steps/Step1ProjectDescription';
import { Step2ArchitecturePreferences } from '../Wizard/steps/Step2ArchitecturePreferences';
import { Step3PlanningConfiguration } from '../Wizard/steps/Step3PlanningConfiguration';
import { Step4StandardsCustomization } from '../Wizard/steps/Step4StandardsCustomization';
import { Wizard, WizardStep } from '../Wizard/Wizard';
import styles from './ProjectWizard.module.css';

export interface ProjectWizardProps {
  onCancel?: () => void;
  onComplete?: (projectId: string) => void;
}

export const ProjectWizard: React.FC<ProjectWizardProps> = ({
  onCancel,
  onComplete,
}) => {
  const navigate = useNavigate();
  const createProjectMutation = useCreateProject();

  const wizardSteps: WizardStep[] = [
    {
      id: 'description',
      title: 'Project Description',
      description: 'Define your project basics and requirements',
      component: Step1ProjectDescription,
    },
    {
      id: 'architecture',
      title: 'Architecture Preferences',
      description: 'Choose your technical architecture and technology stack',
      component: Step2ArchitecturePreferences,
    },
    {
      id: 'planning',
      title: 'Planning Configuration',
      description: 'Configure development methodology and project timeline',
      component: Step3PlanningConfiguration,
    },
    {
      id: 'standards',
      title: 'Standards Customization',
      description: 'Set coding standards and quality requirements',
      component: Step4StandardsCustomization,
    },
  ];

  const handleWizardComplete = async (wizardData: WizardData) => {
    try {
      // Extract data with proper type checking
      const description = isWizardStep1Data(wizardData.description)
        ? wizardData.description
        : {
            projectName: 'Untitled Project',
            projectDescription: '',
            projectType: '',
            targetAudience: '',
          };

      const architecture = isArchitecturePreferences(wizardData.architecture)
        ? wizardData.architecture
        : {
            style: ArchitectureStyle.MICROSERVICES,
            patterns: [],
            technologies: [],
            scalability: ScalabilityLevel.MEDIUM,
          };

      const planning = isPlanningConfiguration(wizardData.planning)
        ? wizardData.planning
        : {
            methodology: DevelopmentMethodology.AGILE,
            phases: [],
            deliverables: [],
            timeline: { duration: 3, unit: TimeUnit.MONTHS, milestones: [] },
          };

      const standards = isStandardsCustomization(wizardData.standards)
        ? wizardData.standards
        : {
            codingStandards: [],
            documentationFormat: DocumentationFormat.MARKDOWN,
            reviewProcesses: [],
            qualityGates: [],
          };

      // Transform wizard data to API format
      const projectData: CreateProjectRequest = {
        name: description.projectName || 'Untitled Project',
        description: description.projectDescription || '',
        settings: {
          architecture,
          planning,
          standards,
        },
      };

      // Create the project
      const newProject = await createProjectMutation.mutateAsync(projectData);

      // Handle completion
      if (onComplete) {
        onComplete(newProject.id);
      } else {
        navigate(ROUTES.PROJECT_DETAIL(newProject.id));
      }
    } catch (error) {
      console.error('Failed to create project:', error);
      // Error is already handled by the mutation's onError
      alert(`Failed to create project: ${handleApiError(error)}`);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      navigate(ROUTES.DASHBOARD);
    }
  };

  return (
    <div className={styles.wizardContainer}>
      <div className={styles.header}>
        <h1>Create New Project</h1>
        <p>
          Follow the steps to configure your project and generate comprehensive
          documentation.
        </p>
      </div>

      <Wizard
        steps={wizardSteps}
        onComplete={handleWizardComplete}
        onCancel={handleCancel}
        className={styles.wizard}
      />
    </div>
  );
};
