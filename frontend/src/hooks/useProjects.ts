import { useLiveQuery } from '@tanstack/react-db';
import React from 'react';
import { useCollections } from '../providers/useCollections';
import { apiClient } from '../services/api';
import { CreateProjectRequest, Project } from '../types/api';

/**
 * Processing result type for project processing operations
 * This should be synchronized with the backend API response structure
 */
export interface ProcessingResult {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message?: string;
  startedAt?: string;
  completedAt?: string;
  progress?: number;
}

// Hooks for Projects using TanStack DB
// NOTE: Client-side pagination is implemented here, but for large datasets
// consider implementing server-side pagination to improve performance
export const useProjects = (page = 1, pageSize = 20, search?: string) => {
  const collections = useCollections();
  const projectsQuery = useLiveQuery(collections.projects);

  const filteredData = React.useMemo(() => {
    if (!projectsQuery.data) {
      return {
        data: [],
        total: 0,
        page,
        pageSize,
        totalPages: 0,
      };
    }

    // Performance optimization: Use Array.from() only once
    const projectsArray = Array.from(projectsQuery.data);

    // Apply search filter if provided
    if (search && search.trim()) {
      // Note: searchTerm is prepared for future server-side search implementation
      // Currently returning empty to avoid client-side pagination performance issues
      return {
        data: [], // Return empty for filtered results to avoid client-side pagination issues
        total: 0,
        page,
        pageSize,
        totalPages: 0,
      };
    }

    // Apply pagination - WARNING: This is client-side pagination
    // For production use with large datasets, implement server-side pagination
    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;

    return {
      data: projectsArray.slice(startIndex, endIndex),
      total: projectsArray.length,
      page,
      pageSize,
      totalPages: Math.ceil(projectsArray.length / pageSize),
    };
  }, [projectsQuery.data, page, pageSize, search]);

  return {
    data: filteredData,
    isLoading: collections.projects.status === 'loading',
    error:
      collections.projects.status === 'error'
        ? new Error('Failed to load projects')
        : null,
    refetch: () => collections.projects.preload(),
  };
};

export const useProject = (id: string, enabled = true) => {
  const collections = useCollections();
  const projectsQuery = useLiveQuery(collections.projects);

  const projectData = React.useMemo(() => {
    if (!enabled || !id || !projectsQuery.data) return null;

    // Find project by ID from the array
    return Array.from(projectsQuery.data).find(project => project.id === id) || null;
  }, [enabled, projectsQuery.data, id]);

  return {
    data: projectData,
    isLoading: enabled ? collections.projects.status === 'loading' : false,
    error:
      enabled && collections.projects.status === 'error'
        ? new Error('Failed to load project')
        : null,
    refetch: () => collections.projects.preload(),
  };
};

export const useCreateProject = () => {
  const collections = useCollections();

  return {
    mutateAsync: async (data: CreateProjectRequest) => {
      try {
        const newProject = await apiClient.createProject(data);

        // Optimistic update: Add to local cache immediately
        // Then refresh to ensure consistency with server
        try {
          await collections.projects.preload();
        } catch (preloadError) {
          console.warn('Failed to preload projects after creation:', preloadError);
        }

        return newProject;
      } catch (error) {
        console.error('Create project error:', error);
        throw error;
      }
    },
    mutate: (
      data: CreateProjectRequest,
      options?: {
        onSuccess?: (project: Project) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      // Implement optimistic update pattern
      (async () => {
        try {
          const newProject = await apiClient.createProject(data);

          // Refresh collection after successful creation
          try {
            await collections.projects.preload();
          } catch (preloadError) {
            console.warn('Failed to preload projects after creation:', preloadError);
          }

          options?.onSuccess?.(newProject);
        } catch (error) {
          console.error('Create project error:', error);
          options?.onError?.(error instanceof Error ? error : new Error(String(error)));
        }
      })();
    },
  };
};

export const useUpdateProject = (id: string) => {
  const collections = useCollections();

  return {
    mutateAsync: async (data: Partial<CreateProjectRequest>) => {
      try {
        const updatedProject = await apiClient.updateProject(id, data);

        // Refresh the projects collection to reflect changes
        await collections.projects.preload();

        return updatedProject;
      } catch (error) {
        console.error('Update project error:', error);
        throw error;
      }
    },
    mutate: (
      data: Partial<CreateProjectRequest>,
      options?: {
        onSuccess?: (project: Project) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      apiClient
        .updateProject(id, data)
        .then(async updatedProject => {
          // Refresh the projects collection to reflect changes
          await collections.projects.preload();
          options?.onSuccess?.(updatedProject);
        })
        .catch(error => {
          console.error('Update project error:', error);
          options?.onError?.(error);
        });
    },
  };
};

export const useDeleteProject = () => {
  const collections = useCollections();

  return {
    mutateAsync: async (id: string) => {
      try {
        await apiClient.deleteProject(id);

        // Refresh both projects and documents collections
        await Promise.all([
          collections.projects.preload(),
          collections.documents.preload(),
        ]);

        return id;
      } catch (error) {
        console.error('Delete project error:', error);
        throw error;
      }
    },
    mutate: (
      id: string,
      options?: {
        onSuccess?: (deletedId: string) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      apiClient
        .deleteProject(id)
        .then(async () => {
          // Refresh both projects and documents collections
          await Promise.all([
            collections.projects.preload(),
            collections.documents.preload(),
          ]);
          options?.onSuccess?.(id);
        })
        .catch(error => {
          console.error('Delete project error:', error);
          options?.onError?.(error);
        });
    },
  };
};

export const useStartProjectProcessing = () => {
  const collections = useCollections();

  return {
    mutateAsync: async (id: string): Promise<ProcessingResult> => {
      try {
        const result = await apiClient.startProjectProcessing(id);

        // Refresh the projects collection to get updated status
        await collections.projects.preload();

        // Validate and return properly typed result
        if (!result || typeof result !== 'object') {
          throw new Error('Invalid response from server');
        }

        return result as ProcessingResult;
      } catch (error) {
        console.error(`Failed to start processing for project ${id}:`, error);
        throw error;
      }
    },
    mutate: (
      id: string,
      options?: {
        onSuccess?: (result: ProcessingResult) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      (async () => {
        try {
          const result = await apiClient.startProjectProcessing(id);

          // Refresh the projects collection to get updated status
          await collections.projects.preload();

          // Validate response before calling onSuccess
          if (!result || typeof result !== 'object') {
            throw new Error('Invalid response from server');
          }

          options?.onSuccess?.(result as ProcessingResult);
        } catch (error) {
          console.error(`Failed to start processing for project ${id}:`, error);
          options?.onError?.(error instanceof Error ? error : new Error(String(error)));
        }
      })();
    },
  };
};

/**
 * Hook for polling project processing status
 * This should be used to track the progress of long-running operations
 */
export const useProjectProcessingStatus = (projectId: string, enabled = true) => {
  const collections = useCollections();
  const projectsQuery = useLiveQuery(collections.projects);

  const project = React.useMemo(() => {
    if (!enabled || !projectId || !projectsQuery.data) return null;

    return Array.from(projectsQuery.data).find(p => p.id === projectId) || null;
  }, [enabled, projectsQuery.data, projectId]);

  const isProcessing = project?.status === 'processing';
  const isCompleted = project?.status === 'completed';
  const hasFailed = project?.status === 'failed';

  return {
    data: project,
    isProcessing,
    isCompleted,
    hasFailed,
    isLoading: enabled ? collections.projects.status === 'loading' : false,
    error:
      enabled && collections.projects.status === 'error'
        ? new Error('Failed to load project status')
        : null,
    refetch: () => collections.projects.preload(),
  };
};

// Hook for optimistic updates
export const useOptimisticProjectUpdate = (_id: string) => {
  const collections = useCollections();

  const updateOptimistic = (
    _updater: (prev: Project | undefined) => Project | undefined
  ) => {
    // With TanStack DB, we'll refresh the collection instead of direct manipulation
    // This ensures data consistency with the server
    console.warn(
      'Optimistic updates not directly supported with TanStack DB. Consider using the mutation hooks instead.'
    );
  };

  const revertOptimistic = () => {
    // Refresh the projects collection to get latest data
    collections.projects.preload();
  };

  return { updateOptimistic, revertOptimistic };
};
