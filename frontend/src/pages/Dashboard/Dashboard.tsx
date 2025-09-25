import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/useAuth';
import { useProjects } from '../../hooks/useProjects';
import { Button } from '../../components/ui/Button/Button';
import { Progress } from '../../components/ui/Progress/Progress';
import { ProjectStatus } from '../../types/api';
import styles from './Dashboard.module.scss';

const DEFAULT_PROJECTS_PAGE = 1;
const DEFAULT_PROJECTS_PAGE_SIZE = 5;

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const {
    data: projectsResponse,
    isLoading,
    error,
  } = useProjects(DEFAULT_PROJECTS_PAGE, DEFAULT_PROJECTS_PAGE_SIZE);

  const recentProjects = projectsResponse?.data || [];

  const getStatusVariant = (status: ProjectStatus) => {
    switch (status) {
      case ProjectStatus.COMPLETED:
        return 'success';
      case ProjectStatus.PROCESSING:
        return 'default';
      case ProjectStatus.FAILED:
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (status: ProjectStatus) => {
    switch (status) {
      case ProjectStatus.DRAFT:
        return 'Draft';
      case ProjectStatus.PROCESSING:
        return 'Processing';
      case ProjectStatus.COMPLETED:
        return 'Completed';
      case ProjectStatus.FAILED:
        return 'Failed';
      default:
        return status;
    }
  };

  if (isLoading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner} />
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2>Error Loading Dashboard</h2>
        <p>Failed to load dashboard data. Please try again.</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      <div className={styles.container}>
        {/* Welcome Section */}
        <section className={styles.welcomeSection}>
          <div className={styles.welcomeContent}>
            <h1 className={styles.welcomeTitle}>Welcome back, {user?.firstName}!</h1>
            <p className={styles.welcomeSubtitle}>
              Create and manage your documentation projects with AI-powered generation.
            </p>
          </div>
          <div className={styles.quickActions}>
            <Button
              variant="primary"
              size="lg"
              onClick={() => navigate('/projects/new')}
            >
              Create New Project
            </Button>
            <Button variant="outline" size="lg" onClick={() => navigate('/projects')}>
              View All Projects
            </Button>
          </div>
        </section>

        {/* Stats Section */}
        <section className={styles.statsSection}>
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statNumber}>{projectsResponse?.total || 0}</div>
              <div className={styles.statLabel}>Total Projects</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statNumber}>
                {
                  recentProjects.filter(p => p.status === ProjectStatus.COMPLETED)
                    .length
                }
              </div>
              <div className={styles.statLabel}>Completed</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statNumber}>
                {
                  recentProjects.filter(p => p.status === ProjectStatus.PROCESSING)
                    .length
                }
              </div>
              <div className={styles.statLabel}>In Progress</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statNumber}>
                {recentProjects.reduce((acc, p) => acc + p.documents.length, 0)}
              </div>
              <div className={styles.statLabel}>Documents Generated</div>
            </div>
          </div>
        </section>

        {/* Recent Projects Section */}
        <section className={styles.projectsSection}>
          <div className={styles.sectionHeader}>
            <h2>Recent Projects</h2>
            <Button variant="ghost" onClick={() => navigate('/projects')}>
              View All
            </Button>
          </div>

          {recentProjects.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>📄</div>
              <h3>No projects yet</h3>
              <p>Create your first project to start generating documentation.</p>
              <Button variant="primary" onClick={() => navigate('/projects/new')}>
                Create Your First Project
              </Button>
            </div>
          ) : (
            <div className={styles.projectsGrid}>
              {recentProjects.map(project => {
                const progressValue = Math.max(0, Math.min(100, project.progress ?? 0));

                return (
                  <div
                    key={project.id}
                    className={styles.projectCard}
                    onClick={() => navigate(`/projects/${project.id}`)}
                  >
                    <div className={styles.projectHeader}>
                      <h3 className={styles.projectName}>{project.name}</h3>
                      <div
                        className={`${styles.statusBadge} ${styles[getStatusVariant(project.status)]}`}
                      >
                        {getStatusLabel(project.status)}
                      </div>
                    </div>

                    <p className={styles.projectDescription}>{project.description}</p>

                    {project.status === ProjectStatus.PROCESSING && (
                      <div className={styles.progressSection}>
                        <Progress
                          value={progressValue}
                          size="sm"
                          variant="default"
                          label="Processing..."
                          showValue
                        />
                      </div>
                    )}

                    <div className={styles.projectFooter}>
                      <div className={styles.projectMeta}>
                        <span>{project.documents.length} documents</span>
                        <span>
                          Updated {new Date(project.updatedAt).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Getting Started Section */}
        <section className={styles.gettingStartedSection}>
          <h2>Getting Started</h2>
          <div className={styles.stepsGrid}>
            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>1</div>
              <h3>Create Project</h3>
              <p>Start by creating a new project and describing your requirements.</p>
            </div>
            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>2</div>
              <h3>Configure Settings</h3>
              <p>
                Choose your architecture, technology stack, and documentation
                preferences.
              </p>
            </div>
            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>3</div>
              <h3>Generate Docs</h3>
              <p>
                Our AI agents will analyze your requirements and generate comprehensive
                documentation.
              </p>
            </div>
            <div className={styles.stepCard}>
              <div className={styles.stepNumber}>4</div>
              <h3>Review & Refine</h3>
              <p>
                Review the generated documents and make iterative improvements as
                needed.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
