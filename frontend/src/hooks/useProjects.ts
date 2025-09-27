import { useLiveQuery } from '@tanstack/react-db';
import React from 'react';
import { useCollections } from '../providers/useCollections';
import { apiClient } from '../services/api';
import { CreateProjectRequest, Project } from '../types/api';

// Hooks for Projects using TanStack DB
export const useProjects = (page = 1, pageSize = 20, search?: string) => {
  const collections = useCollections();
  const projectsQuery = useLiveQuery(collections.projects);

  const filteredData = React.useMemo(() => {
    if (!projectsQuery.data) return [];

    let projects = Array.from(projectsQuery.data);

    // Apply search filter if provided
    if (search && search.trim()) {
      const searchTerm = search.toLowerCase().trim();
      projects = projects.filter(
        project =>
          project.name.toLowerCase().includes(searchTerm) ||
          project.description?.toLowerCase().includes(searchTerm)
      );
    }

    // Apply pagination
    const startIndex = (page - 1) * pageSize;
    const endIndex = startIndex + pageSize;

    return {
      data: projects.slice(startIndex, endIndex),
      total: projects.length,
      page,
      pageSize,
      totalPages: Math.ceil(projects.length / pageSize),
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

    return Array.from(projectsQuery.data).find(project => project.id === id) || null;
  }, [projectsQuery.data, id, enabled]);

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

        // Refresh the projects collection to include the new project
        await collections.projects.preload();

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
      apiClient
        .createProject(data)
        .then(async newProject => {
          // Refresh the projects collection to include the new project
          await collections.projects.preload();
          options?.onSuccess?.(newProject);
        })
        .catch(error => {
          console.error('Create project error:', error);
          options?.onError?.(error);
        });
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
    mutateAsync: async (id: string) => {
      try {
        const result = await apiClient.startProjectProcessing(id);

        // Refresh the projects collection to get updated status
        await collections.projects.preload();

        return result;
      } catch (error) {
        console.error('Start processing error:', error);
        throw error;
      }
    },
    mutate: (
      id: string,
      options?: {
        onSuccess?: (result: unknown) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      apiClient
        .startProjectProcessing(id)
        .then(async result => {
          // Refresh the projects collection to get updated status
          await collections.projects.preload();
          options?.onSuccess?.(result);
        })
        .catch(error => {
          console.error('Start processing error:', error);
          options?.onError?.(error);
        });
    },
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
