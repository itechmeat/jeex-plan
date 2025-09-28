import { useLiveQuery } from '@tanstack/react-db';
import React from 'react';
import { useCollections } from '../providers/useCollections';
import { apiClient } from '../services/api';
import { Document } from '../types/api';

// Hooks for Documents using TanStack DB
export const useProjectDocuments = (projectId: string, enabled = true) => {
  const collections = useCollections();
  const documentsQuery = useLiveQuery(collections.documents);

  const projectDocuments = React.useMemo(() => {
    if (!enabled || !projectId || !documentsQuery.data) return [];

    return documentsQuery.data.filter(document => document.projectId === projectId);
  }, [documentsQuery.data, projectId, enabled]);

  return {
    data: projectDocuments,
    isLoading: enabled ? collections.documents.status === 'loading' : false,
    error:
      enabled && collections.documents.status === 'error'
        ? new Error('Failed to load project documents')
        : null,
    refetch: () => collections.documents.preload(),
  };
};

export const useDocument = (projectId: string, documentId: string, enabled = true) => {
  const collections = useCollections();
  const documentsQuery = useLiveQuery(collections.documents);

  const documentData = React.useMemo(() => {
    if (!enabled || !projectId || !documentId || !documentsQuery.data) return null;

    return (
      documentsQuery.data.find(
        document => document.id === documentId && document.projectId === projectId
      ) || null
    );
  }, [documentsQuery.data, projectId, documentId, enabled]);

  return {
    data: documentData,
    isLoading: enabled ? collections.documents.status === 'loading' : false,
    error:
      enabled && collections.documents.status === 'error'
        ? new Error('Failed to load document')
        : null,
    refetch: () => collections.documents.preload(),
  };
};

export const useUpdateDocument = (projectId: string, documentId: string) => {
  const collections = useCollections();
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

  return {
    mutateAsync: async (content: string) => {
      if (!ensureIds()) {
        return Promise.reject(new Error(missingIdsMessage));
      }

      try {
        const updatedDocument = await apiClient.updateDocument(
          projectId,
          documentId,
          content
        );

        // Refresh the documents collection to reflect changes
        await collections.documents.preload();

        return updatedDocument;
      } catch (error) {
        console.error('Update document error:', error);
        throw error;
      }
    },
    mutate: (
      content: string,
      options?: {
        onSuccess?: (document: Document) => void;
        onError?: (error: Error) => void;
      }
    ) => {
      if (!ensureIds()) {
        options?.onError?.(new Error(missingIdsMessage));
        return;
      }

      apiClient
        .updateDocument(projectId, documentId, content)
        .then(async updatedDocument => {
          // Refresh the documents collection to reflect changes
          await collections.documents.preload();
          options?.onSuccess?.(updatedDocument);
        })
        .catch(error => {
          console.error('Update document error:', error);
          options?.onError?.(error);
        });
    },
  };
};

export const useRegenerateDocument = (projectId: string, documentId: string) => {
  const collections = useCollections();
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

  return {
    mutateAsync: async () => {
      if (!ensureIds()) {
        return Promise.reject(new Error(missingIdsMessage));
      }

      try {
        const result = await apiClient.regenerateDocument(projectId, documentId);

        // Refresh the documents collection to get updated content
        await collections.documents.preload();

        return result;
      } catch (error) {
        console.error('Regenerate document error:', error);
        throw error;
      }
    },
    mutate: (options?: {
      onSuccess?: (result: unknown) => void;
      onError?: (error: Error) => void;
    }) => {
      if (!ensureIds()) {
        options?.onError?.(new Error(missingIdsMessage));
        return;
      }

      apiClient
        .regenerateDocument(projectId, documentId)
        .then(async result => {
          // Refresh the documents collection to get updated content
          await collections.documents.preload();
          options?.onSuccess?.(result);
        })
        .catch(error => {
          console.error('Regenerate document error:', error);
          options?.onError?.(error);
        });
    },
  };
};

// Hook for optimistic document updates
export const useOptimisticDocumentUpdate = (projectId: string, documentId: string) => {
  const collections = useCollections();

  const updateOptimistic = (_content: string) => {
    if (!projectId || !documentId) {
      return;
    }

    // With TanStack DB, we'll refresh the collection instead of direct manipulation
    // This ensures data consistency with the server
    console.warn(
      'Optimistic updates not directly supported with TanStack DB. Consider using the mutation hooks instead.'
    );
  };

  const revertOptimistic = () => {
    if (!projectId || !documentId) {
      return;
    }

    // Refresh the documents collection to get latest data
    collections.documents.preload();
  };

  return { updateOptimistic, revertOptimistic };
};
