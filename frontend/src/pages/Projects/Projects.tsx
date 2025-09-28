import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../../components/ui/Button/Button';
import { Input } from '../../components/ui/Input/Input';
import { Progress } from '../../components/ui/Progress/Progress';
import { useProjects } from '../../hooks/useProjects';
import { ProjectStatus } from '../../types/api';
import styles from './Projects.module.css';

export const Projects: React.FC = () => {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 12;

  const {
    data: projectsResponse,
    isLoading,
    error,
  } = useProjects(page, pageSize, search);

  const projects = projectsResponse?.data || [];
  const totalPages = Math.ceil((projectsResponse?.total || 0) / pageSize);

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

  const handleProjectNavigation = (projectId: string) => {
    navigate(`/projects/${projectId}`);
  };

  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2>Error Loading Projects</h2>
        <p>Failed to load projects. Please try again.</p>
        <Button onClick={() => window.location.reload()}>Retry</Button>
      </div>
    );
  }

  return (
    <div className={styles.projectsPage}>
      <div className={styles.container}>
        <div className={styles.header}>
          <div className={styles.titleSection}>
            <h1>Projects</h1>
            <p>Manage your documentation generation projects</p>
          </div>
          <Button variant='primary' onClick={() => navigate('/projects/new')}>
            Create New Project
          </Button>
        </div>

        <div className={styles.filters}>
          <Input
            placeholder='Search projects...'
            value={search}
            onChange={e => {
              setSearch(e.target.value);
              setPage(1);
            }}
            fullWidth
          />
        </div>

        {isLoading ? (
          <div className={styles.loadingContainer}>
            <div className={styles.spinner} />
            <p>Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIcon}>📄</div>
            <h3>{search ? 'No projects found' : 'No projects yet'}</h3>
            <p>
              {search
                ? 'Try adjusting your search terms.'
                : 'Create your first project to start generating documentation.'}
            </p>
            {!search && (
              <Button variant='primary' onClick={() => navigate('/projects/new')}>
                Create Your First Project
              </Button>
            )}
          </div>
        ) : (
          <>
            <div className={styles.projectsGrid}>
              {projects.map(project => {
                const updatedDate = new Date(project.updatedAt);
                const progressValue = project.progress || 0;
                const statusLabel = project.status.replace('_', ' ').toLowerCase();
                const baseAriaLabel = `${project.name}. ${project.description}. Status: ${statusLabel}.`;
                const ariaLabel =
                  project.status === ProjectStatus.PROCESSING
                    ? `${baseAriaLabel} ${progressValue}% complete.`
                    : baseAriaLabel;

                return (
                  <button
                    key={project.id}
                    className={styles.projectCard}
                    onClick={() => handleProjectNavigation(project.id)}
                    aria-label={ariaLabel}
                  >
                    <div className={styles.projectHeader}>
                      <h3 className={styles.projectName}>{project.name}</h3>
                      <div
                        className={`${styles.statusBadge} ${styles[getStatusVariant(project.status)]}`}
                      >
                        {statusLabel}
                      </div>
                    </div>

                    <p className={styles.projectDescription}>{project.description}</p>

                    {project.status === ProjectStatus.PROCESSING && (
                      <div className={styles.progressSection}>
                        <Progress
                          value={progressValue}
                          size='sm'
                          variant='default'
                          label='Processing...'
                          showValue
                        />
                      </div>
                    )}

                    <div className={styles.projectFooter}>
                      <div className={styles.projectMeta}>
                        <span>{project.documents.length} documents</span>
                        <span>Updated {updatedDate.toLocaleDateString()}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>

            {totalPages > 1 && (
              <div className={styles.pagination}>
                <Button
                  variant='outline'
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <span className={styles.pageInfo}>
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant='outline'
                  disabled={page === totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
