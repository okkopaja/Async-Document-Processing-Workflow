import { useEffect, useRef, useState } from 'react';
import { ProgressEvent } from '@/types';
import { getWebSocketUrl } from '@/lib/endpoints';
import { WSClient } from '@/lib/ws-client';

interface JobProgressHookState {
  events: ProgressEvent[];
  latestEvent: ProgressEvent | null;
  isConnected: boolean;
  error: string | null;
}

interface JobProgressStateInternal extends JobProgressHookState {
  sourceId: string | null;
}

const EMPTY_STATE: JobProgressStateInternal = {
  sourceId: null,
  events: [],
  latestEvent: null,
  isConnected: false,
  error: null,
};

/**
 * Hook for subscribing to real-time job progress events.
 * 
 * Automatically manages WebSocket connection lifecycle and reconnection.
 * Frontend should use REST API to recover state if WebSocket is down.
 */
export function useJobProgress(jobId: string | null) {
  const [state, setState] = useState<JobProgressStateInternal>(EMPTY_STATE);

  const wsClientRef = useRef<WSClient | null>(null);

  // Initialize and manage WebSocket connection
  useEffect(() => {
    if (!jobId) {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
      return;
    }

    // Create WSClient if not already created
    if (!wsClientRef.current) {
      wsClientRef.current = new WSClient({
        maxRetries: 10,
        initialDelayMs: 1000,
        maxDelayMs: 30000,
      });
    }

    const wsClient = wsClientRef.current;

    // Handle incoming progress events
    const handleMessage = (event: ProgressEvent) => {
      setState((prev) => ({
        ...prev,
        sourceId: jobId,
        events: [...prev.events, event],
        latestEvent: event,
        error: null,
      }));
    };

    // Handle connection state changes
    const handleStateChange = (isConnected: boolean) => {
      setState((prev) => ({
        ...prev,
        sourceId: jobId,
        isConnected,
        error: isConnected ? null : 'WebSocket disconnected',
      }));
    };

    // Connect to WebSocket endpoint
    const url = getWebSocketUrl(`/ws/jobs/${jobId}`);

    wsClient.onMessage(handleMessage);
    wsClient.onStateChange(handleStateChange);
    wsClient.connect(url);

    // Cleanup: Remove handlers on unmount (but keep client for potential reuse)
    return () => {
      if (wsClient) {
        wsClient.offMessage(handleMessage);
        wsClient.offStateChange(handleStateChange);
      }
    };
  }, [jobId]);

  // Disconnect completely on component unmount
  useEffect(() => {
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
    };
  }, []);

  if (!jobId || state.sourceId !== jobId) {
    return {
      events: [],
      latestEvent: null,
      isConnected: false,
      error: null,
    } satisfies JobProgressHookState;
  }

  return {
    events: state.events,
    latestEvent: state.latestEvent,
    isConnected: state.isConnected,
    error: state.error,
  } satisfies JobProgressHookState;
}
