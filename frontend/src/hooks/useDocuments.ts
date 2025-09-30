import { useLiveQuery } from '@tanstack/react-db';
import React from 'react';
import { useCollections } from '../providers/useCollections';
import { apiClient } from '../services/api';
import { Document } from '../types/api';

/**
 * MIGRATION NOTE: useLiveQuery is the correct TanStack DB hook for reactive queries
 * The old useApiQuery was from a different library and has been replaced
 * useLiveQuery provides real-time updates from the local TanStack DB instance
 */

// Hooks for Documents using TanStack DB
export const useProjectDocuments = (projectId: string, enabled = true) => {
  const collections = useCollections();
  const documentsQuery = useLiveQuery(collections.documents);

  // NOTE: Client-side filtering is used here because the documents collection
  // fetches all documents for all projects in a single sync operation.
  // Future optimization: Implement server-side filtering or create indexed queries
  // in TanStack DB to efficiently look up documents by projectId without full scans.
  const projectDocuments = React.useMemo(() => {
    if (!enabled || !projectId || !documentsQuery.data) return [];

    // Use Array.from to ensure we have a proper array before filtering
    const documentsArray = Array.from(documentsQuery.data);
    return documentsArray.filter(document => document.projectId === projectId);
  }, [documentsQuery.data, projectId, enabled]);

  return {
    data: projectDocuments,
    isLoading: enabled ? collections.documents.status === 'loading' : false,
    error:
      enabled && collections.documents.status === 'error'
        ? new Error('Failed to load documents')
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
  }, [enabled, documentsQuery.data, projectId, documentId]);

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

    if (import.meta.env.DEV) {
      console.warn(missingIdsMessage);
    }
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
        // Production-safe error handling with context preservation
        const errorContext = {
          projectId,
          documentId,
          timestamp: new Date().toISOString(),
        };

        // In development, log detailed error context
        if (import.meta.env.DEV) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          console.error(
            `Failed to update document ${documentId} in project ${projectId}:`,
            {
              error: errorMessage,
              ...errorContext,
            }
          );
        }

        // Preserve original error with context for production error tracking
        const enhancedError =
          error instanceof Error
            ? new Error(
                `${error.message} (Project: ${projectId}, Document: ${documentId})`
              )
            : new Error(
                `Failed to update document ${documentId} in project ${projectId}`
              );

        // Copy original error properties
        if (error instanceof Error) {
          enhancedError.stack = error.stack;
          enhancedError.name = error.name;
        }

        throw enhancedError;
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

      // Wrap updateDocument + preload in try/catch with context logging
      (async () => {
        try {
          const updatedDocument = await apiClient.updateDocument(
            projectId,
            documentId,
            content
          );

          // Refresh the documents collection to reflect changes
          await collections.documents.preload();

          options?.onSuccess?.(updatedDocument);
        } catch (error) {
          // Production-safe error handling with context preservation
          const errorContext = {
            projectId,
            documentId,
            timestamp: new Date().toISOString(),
          };

          // In development, log detailed error context
          if (import.meta.env.DEV) {
            const errorMessage =
              error instanceof Error ? error.message : 'Unknown error';
            console.error(
              `Failed to update document ${documentId} in project ${projectId}:`,
              {
                error: errorMessage,
                ...errorContext,
              }
            );
          }

          // Preserve original error with context for production error tracking
          const enhancedError =
            error instanceof Error
              ? new Error(
                  `${error.message} (Project: ${projectId}, Document: ${documentId})`
                )
              : new Error(
                  `Failed to update document ${documentId} in project ${projectId}`
                );

          // Copy original error properties
          if (error instanceof Error) {
            enhancedError.stack = error.stack;
            enhancedError.name = error.name;
          }

          options?.onError?.(enhancedError);
        }
      })();
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

    if (import.meta.env.DEV) {
      console.warn(missingIdsMessage);
    }
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
        // Separate API call from preload for better error handling
        const result = await apiClient.regenerateDocument(projectId, documentId);

        // Refresh the documents collection to get updated content
        // This is done after the successful API call
        try {
          await collections.documents.preload();
        } catch (preloadError) {
          // Log preload error but don't fail the operation
          if (import.meta.env.DEV) {
            console.warn(
              `Failed to preload documents after regenerating ${documentId}:`,
              preloadError
            );
          }
        }

        return result;
      } catch (error) {
        // Production-safe error handling with context preservation
        const errorContext = {
          projectId,
          documentId,
          timestamp: new Date().toISOString(),
        };

        // In development, log detailed error context
        if (import.meta.env.DEV) {
          const errorMessage = error instanceof Error ? error.message : 'Unknown error';
          console.error(
            `Failed to regenerate document ${documentId} in project ${projectId}:`,
            {
              error: errorMessage,
              ...errorContext,
            }
          );
        }

        // Preserve original error with context for production error tracking
        const enhancedError =
          error instanceof Error
            ? new Error(
                `${error.message} (Project: ${projectId}, Document: ${documentId})`
              )
            : new Error(
                `Failed to regenerate document ${documentId} in project ${projectId}`
              );

        // Copy original error properties
        if (error instanceof Error) {
          enhancedError.stack = error.stack;
          enhancedError.name = error.name;
        }

        throw enhancedError;
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

      // Wrap API call and preload separately for better error handling
      (async () => {
        try {
          // Separate API call from preload
          const result = await apiClient.regenerateDocument(projectId, documentId);

          // Handle preload separately to avoid failing the main operation
          try {
            await collections.documents.preload();
          } catch (preloadError) {
            if (import.meta.env.DEV) {
              console.warn(
                `Failed to preload documents after regenerating ${documentId}:`,
                preloadError
              );
            }
          }

          options?.onSuccess?.(result);
        } catch (error) {
          // Production-safe error handling with context preservation
          const errorContext = {
            projectId,
            documentId,
            timestamp: new Date().toISOString(),
          };

          // In development, log detailed error context
          if (import.meta.env.DEV) {
            const errorMessage =
              error instanceof Error ? error.message : 'Unknown error';
            console.error(
              `Failed to regenerate document ${documentId} in project ${projectId}:`,
              {
                error: errorMessage,
                ...errorContext,
              }
            );
          }

          // Preserve original error with context for production error tracking
          const enhancedError =
            error instanceof Error
              ? new Error(
                  `${error.message} (Project: ${projectId}, Document: ${documentId})`
                )
              : new Error(
                  `Failed to regenerate document ${documentId} in project ${projectId}`
                );

          // Copy original error properties
          if (error instanceof Error) {
            enhancedError.stack = error.stack;
            enhancedError.name = error.name;
          }

          options?.onError?.(enhancedError);
        }
      })();
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
    if (import.meta.env.DEV) {
      console.warn(
        'Optimistic updates not directly supported with TanStack DB. Consider using the mutation hooks instead.'
      );
    }
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
