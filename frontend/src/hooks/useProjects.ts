import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { Project, CreateProjectRequest } from '../types/api';

// Query Keys
const QUERY_KEYS = {
  projects: ['projects'] as const,
  project: (id: string) => ['projects', id] as const,
  projectDocuments: (id: string) => ['projects', id, 'documents'] as const,
};

// Hooks for Projects
export const useProjects = (page = 1, pageSize = 20, search?: string) => {
  return useQuery({
    queryKey: [...QUERY_KEYS.projects, page, pageSize, search],
    queryFn: () => apiClient.getProjects(page, pageSize, search),
    placeholderData: previousData => previousData,
  });
};

export const useProject = (id: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.project(id),
    queryFn: () => apiClient.getProject(id),
    enabled: enabled && Boolean(id),
  });
};

export const useCreateProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProjectRequest) => apiClient.createProject(data),
    onSuccess: newProject => {
      // Invalidate projects list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.projects });

      // Add new project to cache
      queryClient.setQueryData(QUERY_KEYS.project(newProject.id), newProject);
    },
    onError: error => {
      console.error('Create project error:', error);
    },
  });
};

export const useUpdateProject = (id: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<CreateProjectRequest>) =>
      apiClient.updateProject(id, data),
    onSuccess: updatedProject => {
      // Update project in cache
      queryClient.setQueryData(QUERY_KEYS.project(id), updatedProject);

      // Invalidate projects list to reflect changes
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.projects });
    },
    onError: error => {
      console.error('Update project error:', error);
    },
  });
};

export const useDeleteProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiClient.deleteProject(id),
    onSuccess: (_, id) => {
      // Remove project from cache
      queryClient.removeQueries({ queryKey: QUERY_KEYS.project(id) });

      // Remove project documents from cache
      queryClient.removeQueries({ queryKey: QUERY_KEYS.projectDocuments(id) });

      // Invalidate projects list
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.projects });
    },
    onError: error => {
      console.error('Delete project error:', error);
    },
  });
};

export const useStartProjectProcessing = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => apiClient.startProjectProcessing(id),
    onSuccess: (_, id) => {
      // Invalidate project to get updated status
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.project(id) });
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.projects });
    },
    onError: error => {
      console.error('Start processing error:', error);
    },
  });
};

// Hook for optimistic updates
export const useOptimisticProjectUpdate = (id: string) => {
  const queryClient = useQueryClient();

  const updateOptimistic = (
    updater: (prev: Project | undefined) => Project | undefined
  ) => {
    queryClient.setQueryData(QUERY_KEYS.project(id), updater);
  };

  const revertOptimistic = () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.project(id) });
  };

  return { updateOptimistic, revertOptimistic };
};
