import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';
import { Document } from '../types/api';

// Query Keys
const QUERY_KEYS = {
  projectDocuments: (projectId: string) =>
    ['projects', projectId, 'documents'] as const,
  document: (projectId: string, documentId: string) =>
    ['projects', projectId, 'documents', documentId] as const,
};

// Hooks for Documents
export const useProjectDocuments = (projectId: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.projectDocuments(projectId),
    queryFn: () => apiClient.getProjectDocuments(projectId),
    enabled: enabled && Boolean(projectId),
  });
};

export const useDocument = (projectId: string, documentId: string, enabled = true) => {
  return useQuery({
    queryKey: QUERY_KEYS.document(projectId, documentId),
    queryFn: () => apiClient.getDocument(projectId, documentId),
    enabled: enabled && Boolean(projectId) && Boolean(documentId),
  });
};

export const useUpdateDocument = (projectId: string, documentId: string) => {
  const queryClient = useQueryClient();
  const idsValid = Boolean(projectId) && Boolean(documentId);
  const missingIdsMessage =
    'useUpdateDocument requires both projectId and documentId to be provided';

  const ensureIds = () => {
    if (Boolean(projectId) && Boolean(documentId)) {
      return true;
    }

    if (import.meta.env.DEV) {
      throw new Error(missingIdsMessage);
    }

    console.warn(missingIdsMessage);
    return false;
  };

  if (!idsValid && import.meta.env.DEV) {
    throw new Error(missingIdsMessage);
  }

  return useMutation({
    mutationFn: async (content: string) => {
      if (!ensureIds()) {
        return Promise.reject(new Error(missingIdsMessage));
      }

      return apiClient.updateDocument(projectId, documentId, content);
    },
    onSuccess: updatedDocument => {
      if (!ensureIds()) {
        return;
      }

      // Update document in cache
      queryClient.setQueryData(
        QUERY_KEYS.document(projectId, documentId),
        updatedDocument
      );

      // Update document in project documents list
      queryClient.setQueryData(
        QUERY_KEYS.projectDocuments(projectId),
        (prev: Document[] | undefined) => {
          if (!prev) return prev;
          return prev.map(doc => (doc.id === documentId ? updatedDocument : doc));
        }
      );
    },
    onError: error => {
      console.error('Update document error:', error);
    },
  });
};

export const useRegenerateDocument = (projectId: string, documentId: string) => {
  const queryClient = useQueryClient();
  const idsValid = Boolean(projectId) && Boolean(documentId);
  const missingIdsMessage =
    'useRegenerateDocument requires both projectId and documentId to be provided';

  const ensureIds = () => {
    if (Boolean(projectId) && Boolean(documentId)) {
      return true;
    }

    if (import.meta.env.DEV) {
      throw new Error(missingIdsMessage);
    }

    console.warn(missingIdsMessage);
    return false;
  };

  if (!idsValid && import.meta.env.DEV) {
    throw new Error(missingIdsMessage);
  }

  return useMutation({
    mutationFn: async () => {
      if (!ensureIds()) {
        return Promise.reject(new Error(missingIdsMessage));
      }

      return apiClient.regenerateDocument(projectId, documentId);
    },
    onSuccess: () => {
      if (!ensureIds()) {
        return;
      }

      // Invalidate document to refetch updated content
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.document(projectId, documentId),
      });

      // Also invalidate project documents list
      queryClient.invalidateQueries({
        queryKey: QUERY_KEYS.projectDocuments(projectId),
      });
    },
    onError: error => {
      console.error('Regenerate document error:', error);
    },
  });
};

// Hook for optimistic document updates
export const useOptimisticDocumentUpdate = (projectId: string, documentId: string) => {
  const queryClient = useQueryClient();

  const updateOptimistic = (content: string) => {
    if (!projectId || !documentId) {
      return;
    }

    queryClient.setQueryData(
      QUERY_KEYS.document(projectId, documentId),
      (prev: Document | undefined) => {
        if (!prev) return prev;
        return {
          ...prev,
          content,
          updatedAt: new Date().toISOString(),
        };
      }
    );
  };

  const revertOptimistic = () => {
    if (!projectId || !documentId) {
      return;
    }

    queryClient.invalidateQueries({
      queryKey: QUERY_KEYS.document(projectId, documentId),
    });
  };

  return { updateOptimistic, revertOptimistic };
};
