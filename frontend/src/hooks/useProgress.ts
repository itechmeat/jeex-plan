import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiClient } from '../services/api';
import { ProcessingStep, ProgressUpdate } from '../types/api';

interface UseProgressOptions {
  projectId: string;
  enabled?: boolean;
  onProgress?: (update: ProgressUpdate) => void;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

interface UseProgressReturn {
  progress: ProgressUpdate | null;
  isConnected: boolean;
  error: string | null;
  disconnect: () => void;
  reconnect: () => void;
}

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  if (typeof error === 'string' && error.trim().length > 0) {
    return error;
  }

  if (error && typeof error === 'object') {
    const { message, data } = error as { message?: unknown; data?: unknown };

    if (typeof message === 'string' && message.trim().length > 0) {
      return message;
    }

    if (typeof data === 'string' && data.trim().length > 0) {
      return data;
    }
  }

  if (error !== undefined && error !== null) {
    try {
      const stringified = JSON.stringify(error);
      if (stringified && stringified !== '{}') {
        return stringified;
      }
    } catch {
      // ignore JSON stringify errors and fall back
    }
  }

  return fallback;
};

export const useProgress = ({
  projectId,
  enabled = true,
  onProgress,
  onComplete,
  onError,
}: UseProgressOptions): UseProgressReturn => {
  const [progress, setProgress] = useState<ProgressUpdate | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
    reconnectAttempts.current = 0;
  }, []);

  const connect = useCallback(() => {
    if (!enabled || !projectId || eventSourceRef.current) {
      return;
    }

    try {
      const eventSource = apiClient.createProgressEventSource(projectId);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      eventSource.onmessage = event => {
        try {
          const update: ProgressUpdate = JSON.parse(event.data);
          setProgress(update);
          onProgress?.(update);

          // Check if processing is complete
          if (update.step === ProcessingStep.COMPLETED) {
            onComplete?.();
          }
        } catch (parseError) {
          console.error('Failed to parse progress update:', parseError);
          const errorMessage = getErrorMessage(
            parseError,
            'Failed to parse progress data'
          );
          setError(errorMessage);
          onError?.(errorMessage);
        }
      };

      eventSource.onerror = event => {
        console.error('EventSource error:', event);
        setIsConnected(false);

        const errorMessage = getErrorMessage(
          event,
          'Connection to progress updates lost'
        );
        setError(errorMessage);
        onError?.(errorMessage);

        // Implement exponential backoff for reconnection
        const maxReconnectAttempts = 5;
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);

          reconnectTimeoutRef.current = setTimeout(() => {
            if (enabled && projectId) {
              disconnect();
              connect();
            }
          }, delay);
        } else {
          const finalErrorMessage = getErrorMessage(
            event,
            'Failed to connect to progress updates after multiple attempts'
          );
          setError(finalErrorMessage);
          onError?.(finalErrorMessage);
        }
      };
    } catch (error) {
      console.error('Failed to establish connection to progress updates:', error);
      const errorMessage = getErrorMessage(
        error,
        'Failed to establish connection to progress updates'
      );
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, [enabled, projectId, onProgress, onComplete, onError, disconnect]);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    setError(null);
    connect();
  }, [disconnect, connect]);

  // Effect to manage connection lifecycle
  useEffect(() => {
    if (enabled && projectId) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, projectId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    progress,
    isConnected,
    error,
    disconnect,
    reconnect,
  };
};

// Hook for multiple project progress tracking
type MultiProgressInternalState = {
  progress: ProgressUpdate | null;
  isConnected: boolean;
  error: string | null;
};

const defaultMultiProgressState: MultiProgressInternalState = {
  progress: null,
  isConnected: false,
  error: null,
};

export const useMultipleProgress = (
  projectIds: string[],
  enabled = true
): Record<string, UseProgressReturn> => {
  const enabledRef = useRef(enabled);
  const [progressStates, setProgressStates] = useState<
    Record<string, MultiProgressInternalState>
  >({});
  const progressStatesRef = useRef<Record<string, MultiProgressInternalState>>({});

  const eventSourcesRef = useRef<Record<string, EventSource | null>>({});
  const reconnectTimeoutsRef = useRef<
    Record<string, ReturnType<typeof setTimeout> | null>
  >({});
  const reconnectAttemptsRef = useRef<Record<string, number>>({});

  useEffect(() => {
    enabledRef.current = enabled;
  }, [enabled]);

  useEffect(() => {
    progressStatesRef.current = progressStates;
  }, [progressStates]);

  const ensureState = useCallback((projectId: string) => {
    setProgressStates(prev => {
      if (prev[projectId]) {
        return prev;
      }

      return {
        ...prev,
        [projectId]: { ...defaultMultiProgressState },
      };
    });
  }, []);

  const updateState = useCallback(
    (projectId: string, partial: Partial<MultiProgressInternalState>) => {
      setProgressStates(prev => {
        const previous = prev[projectId] ?? defaultMultiProgressState;
        const nextState: MultiProgressInternalState = {
          ...previous,
          ...partial,
        };

        if (
          previous.progress === nextState.progress &&
          previous.isConnected === nextState.isConnected &&
          previous.error === nextState.error
        ) {
          return prev;
        }

        return {
          ...prev,
          [projectId]: nextState,
        };
      });
    },
    []
  );

  const removeState = useCallback((projectId: string) => {
    setProgressStates(prev => {
      if (!(projectId in prev)) {
        return prev;
      }

      const { [projectId]: _, ...rest } = prev;
      void _;
      return rest;
    });

    delete reconnectAttemptsRef.current[projectId];
  }, []);

  const clearReconnectTimeout = useCallback((projectId: string) => {
    const timeout = reconnectTimeoutsRef.current[projectId];
    if (timeout) {
      clearTimeout(timeout);
    }
    delete reconnectTimeoutsRef.current[projectId];
  }, []);

  const closeEventSource = useCallback(
    (projectId: string) => {
      const source = eventSourcesRef.current[projectId];
      if (source) {
        source.close();
      }
      delete eventSourcesRef.current[projectId];
      clearReconnectTimeout(projectId);
    },
    [clearReconnectTimeout]
  );

  const disconnectProject = useCallback(
    (projectId: string) => {
      closeEventSource(projectId);
      reconnectAttemptsRef.current[projectId] = 0;
      updateState(projectId, { isConnected: false });
    },
    [closeEventSource, updateState]
  );

  const connectProject = useCallback(
    (projectId: string) => {
      if (!enabledRef.current || !projectId || eventSourcesRef.current[projectId]) {
        return;
      }

      try {
        ensureState(projectId);
        const eventSource = apiClient.createProgressEventSource(projectId);
        eventSourcesRef.current[projectId] = eventSource;

        eventSource.onopen = () => {
          const pendingTimeout = reconnectTimeoutsRef.current[projectId];
          if (pendingTimeout) {
            clearTimeout(pendingTimeout);
            delete reconnectTimeoutsRef.current[projectId];
          }
          reconnectAttemptsRef.current[projectId] = 0;
          updateState(projectId, {
            isConnected: true,
            error: null,
          });
        };

        eventSource.onmessage = event => {
          try {
            const update: ProgressUpdate = JSON.parse(event.data);
            updateState(projectId, {
              progress: update,
            });
          } catch (parseError) {
            console.error('Failed to parse progress update:', parseError);
            const errorMessage = getErrorMessage(
              parseError,
              'Failed to parse progress data'
            );
            updateState(projectId, {
              error: errorMessage,
            });
          }
        };

        eventSource.onerror = event => {
          console.error('EventSource error:', event);
          closeEventSource(projectId);
          updateState(projectId, { isConnected: false });

          const errorMessage = getErrorMessage(
            event,
            'Connection to progress updates lost'
          );
          updateState(projectId, {
            error: errorMessage,
          });

          const maxReconnectAttempts = 5;
          const attempts = (reconnectAttemptsRef.current[projectId] ?? 0) + 1;

          if (attempts <= maxReconnectAttempts) {
            reconnectAttemptsRef.current[projectId] = attempts;
            const delay = Math.min(1000 * Math.pow(2, attempts), 30000);

            reconnectTimeoutsRef.current[projectId] = setTimeout(() => {
              if (!enabledRef.current) {
                return;
              }
              connectProject(projectId);
            }, delay);
          } else {
            reconnectAttemptsRef.current[projectId] = 0;
            const finalErrorMessage = getErrorMessage(
              event,
              'Failed to connect to progress updates after multiple attempts'
            );
            updateState(projectId, {
              error: finalErrorMessage,
            });
          }
        };
      } catch (error) {
        console.error('Failed to establish connection to progress updates:', error);
        const errorMessage = getErrorMessage(
          error,
          'Failed to establish connection to progress updates'
        );
        updateState(projectId, {
          error: errorMessage,
        });
      }
    },
    [closeEventSource, ensureState, updateState]
  );

  const reconnectProject = useCallback(
    (projectId: string) => {
      disconnectProject(projectId);
      updateState(projectId, { error: null });
      connectProject(projectId);
    },
    [connectProject, disconnectProject, updateState]
  );

  useEffect(() => {
    const activeProjectIds = new Set(projectIds);
    const currentEventSources = eventSourcesRef.current;
    const currentTimeouts = reconnectTimeoutsRef.current;

    Object.keys(currentEventSources).forEach(projectId => {
      if (!activeProjectIds.has(projectId)) {
        disconnectProject(projectId);
        removeState(projectId);
      }
    });

    Object.keys(currentTimeouts).forEach(projectId => {
      if (!activeProjectIds.has(projectId)) {
        clearReconnectTimeout(projectId);
      }
    });

    Object.keys(progressStatesRef.current).forEach(projectId => {
      if (!activeProjectIds.has(projectId)) {
        removeState(projectId);
      }
    });

    projectIds.forEach(projectId => {
      ensureState(projectId);
    });

    if (!enabled) {
      projectIds.forEach(projectId => {
        disconnectProject(projectId);
      });
      return;
    }

    projectIds.forEach(projectId => {
      connectProject(projectId);
    });
  }, [
    projectIds,
    enabled,
    clearReconnectTimeout,
    connectProject,
    disconnectProject,
    ensureState,
    removeState,
  ]);

  useEffect(() => {
    const currentEventSources = eventSourcesRef.current;
    const currentTimeouts = reconnectTimeoutsRef.current;

    return () => {
      Object.keys(currentEventSources).forEach(projectId => {
        disconnectProject(projectId);
      });
      Object.keys(currentTimeouts).forEach(projectId => {
        clearReconnectTimeout(projectId);
      });
    };
  }, [clearReconnectTimeout, disconnectProject]);

  const multiProgress = useMemo(() => {
    const entries = Object.entries(progressStates);
    const result: Record<string, UseProgressReturn> = {};

    entries.forEach(([projectId, state]) => {
      result[projectId] = {
        progress: state.progress,
        isConnected: state.isConnected,
        error: state.error,
        disconnect: () => disconnectProject(projectId),
        reconnect: () => reconnectProject(projectId),
      };
    });

    return result;
  }, [disconnectProject, progressStates, reconnectProject]);

  return multiProgress;
};

// Utility function to get progress percentage
export const getProgressPercentage = (update: ProgressUpdate | null): number => {
  if (!update) return 0;

  const stepWeights: Record<ProcessingStep, number> = {
    [ProcessingStep.INITIALIZING]: 10,
    [ProcessingStep.ANALYZING]: 25,
    [ProcessingStep.PLANNING]: 40,
    [ProcessingStep.GENERATING_DOCS]: 70,
    [ProcessingStep.REVIEWING]: 85,
    [ProcessingStep.FINALIZING]: 95,
    [ProcessingStep.COMPLETED]: 100,
    [ProcessingStep.ERROR]: 0,
  };

  const baseProgress = stepWeights[update.step] || 0;
  const stepProgress = (update.progress / 100) * 10; // Each step contributes up to 10% additional progress

  return Math.min(100, baseProgress + stepProgress);
};

// Utility function to get step display name
export const getStepDisplayName = (step: ProcessingStep): string => {
  const displayNames: Record<ProcessingStep, string> = {
    [ProcessingStep.INITIALIZING]: 'Initializing',
    [ProcessingStep.ANALYZING]: 'Analyzing Requirements',
    [ProcessingStep.PLANNING]: 'Planning Architecture',
    [ProcessingStep.GENERATING_DOCS]: 'Generating Documents',
    [ProcessingStep.REVIEWING]: 'Reviewing Content',
    [ProcessingStep.FINALIZING]: 'Finalizing',
    [ProcessingStep.COMPLETED]: 'Completed',
    [ProcessingStep.ERROR]: 'Error',
  };

  return displayNames[step] || step;
};
