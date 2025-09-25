// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Authentication Types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export interface RefreshTokenRequest {
  refreshToken: string;
}

// User Types
export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  tenantId: string;
  createdAt: string;
  updatedAt: string;
}

export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
}

// Project Types
export interface Project {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  progress?: number;
  tenantId: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
  documents: Document[];
  settings: ProjectSettings;
}

export enum ProjectStatus {
  DRAFT = 'draft',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface ProjectSettings {
  architecture: ArchitecturePreferences;
  planning: PlanningConfiguration;
  standards: StandardsCustomization;
}

export interface CreateProjectRequest {
  name: string;
  description: string;
  settings: ProjectSettings;
}

// Document Types
export interface Document {
  id: string;
  name: string;
  content: string;
  type: DocumentType;
  projectId: string;
  version: number;
  status: DocumentStatus;
  createdAt: string;
  updatedAt: string;
}

export enum DocumentType {
  TECHNICAL_SPEC = 'technical_spec',
  API_DOCS = 'api_docs',
  USER_GUIDE = 'user_guide',
  ARCHITECTURE = 'architecture',
  README = 'readme',
}

export enum DocumentStatus {
  DRAFT = 'draft',
  GENERATING = 'generating',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// Wizard Step Types
export interface WizardStep1Data {
  projectName: string;
  projectDescription: string;
  projectType: string;
  targetAudience: string;
}

export interface ArchitecturePreferences {
  style: ArchitectureStyle;
  patterns: string[];
  technologies: string[];
  scalability: ScalabilityLevel;
}

export enum ArchitectureStyle {
  MICROSERVICES = 'microservices',
  MONOLITHIC = 'monolithic',
  SERVERLESS = 'serverless',
  EVENT_DRIVEN = 'event_driven',
}

export enum ScalabilityLevel {
  SMALL = 'small',
  MEDIUM = 'medium',
  LARGE = 'large',
  ENTERPRISE = 'enterprise',
}

export interface PlanningConfiguration {
  methodology: DevelopmentMethodology;
  phases: string[];
  deliverables: string[];
  timeline: TimelinePreferences;
}

export enum DevelopmentMethodology {
  AGILE = 'agile',
  WATERFALL = 'waterfall',
  HYBRID = 'hybrid',
}

export interface TimelinePreferences {
  duration: number;
  unit: TimeUnit;
  milestones: string[];
}

export enum TimeUnit {
  WEEKS = 'weeks',
  MONTHS = 'months',
  QUARTERS = 'quarters',
}

export interface StandardsCustomization {
  codingStandards: string[];
  documentationFormat: DocumentationFormat;
  reviewProcesses: string[];
  qualityGates: string[];
}

export enum DocumentationFormat {
  MARKDOWN = 'markdown',
  CONFLUENCE = 'confluence',
  NOTION = 'notion',
  CUSTOM = 'custom',
}

// Complete Wizard Data Type
export interface WizardData {
  description?: WizardStep1Data;
  architecture?: ArchitecturePreferences;
  planning?: PlanningConfiguration;
  standards?: StandardsCustomization;
}

// Type guards for wizard data
export const isWizardStep1Data = (data: unknown): data is WizardStep1Data => {
  if (typeof data !== 'object' || data === null) return false;
  const obj = data as Record<string, unknown>;
  return (
    'projectName' in obj &&
    typeof obj.projectName === 'string' &&
    'projectDescription' in obj &&
    typeof obj.projectDescription === 'string' &&
    'projectType' in obj &&
    typeof obj.projectType === 'string' &&
    'targetAudience' in obj &&
    typeof obj.targetAudience === 'string'
  );
};

export const isArchitecturePreferences = (
  data: unknown
): data is ArchitecturePreferences => {
  if (typeof data !== 'object' || data === null) return false;
  const obj = data as Record<string, unknown>;
  return (
    'style' in obj &&
    typeof obj.style === 'string' &&
    'patterns' in obj &&
    Array.isArray(obj.patterns)
  );
};

export const isPlanningConfiguration = (
  data: unknown
): data is PlanningConfiguration => {
  if (typeof data !== 'object' || data === null) return false;
  const obj = data as Record<string, unknown>;
  return (
    'methodology' in obj &&
    typeof obj.methodology === 'string' &&
    'phases' in obj &&
    Array.isArray(obj.phases)
  );
};

export const isStandardsCustomization = (
  data: unknown
): data is StandardsCustomization => {
  if (typeof data !== 'object' || data === null) return false;
  const obj = data as Record<string, unknown>;
  return (
    'codingStandards' in obj &&
    Array.isArray(obj.codingStandards) &&
    'documentationFormat' in obj &&
    typeof obj.documentationFormat === 'string'
  );
};

export const isTimelinePreferences = (data: unknown): data is TimelinePreferences => {
  if (typeof data !== 'object' || data === null) return false;
  const obj = data as Record<string, unknown>;
  return (
    'duration' in obj &&
    typeof obj.duration === 'number' &&
    'unit' in obj &&
    typeof obj.unit === 'string' &&
    'milestones' in obj &&
    Array.isArray(obj.milestones)
  );
};

// Progress Tracking Types
export interface ProgressUpdate {
  projectId: string;
  step: ProcessingStep;
  progress: number;
  message: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export enum ProcessingStep {
  INITIALIZING = 'initializing',
  ANALYZING = 'analyzing',
  PLANNING = 'planning',
  GENERATING_DOCS = 'generating_docs',
  REVIEWING = 'reviewing',
  FINALIZING = 'finalizing',
  COMPLETED = 'completed',
  ERROR = 'error',
}

// Error Types
export interface ApiError {
  message: string;
  code: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

// Health Check Types
export interface HealthStatus {
  status: 'pass' | 'fail' | 'warn';
  services: HealthCheck[];
  overall?: {
    status: 'pass' | 'fail' | 'warn';
    totalServices: number;
    healthyServices: number;
    warningServices: number;
    failedServices: number;
    lastUpdated: string;
  };
}

export interface HealthCheck {
  service: string;
  endpoint: string;
  status: 'pass' | 'fail' | 'warn';
  responseTime: number;
  details: string;
  timestamp: string;
  version?: string;
  uptime?: number;
}
