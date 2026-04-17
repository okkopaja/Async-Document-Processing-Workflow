import { useEffect, useRef, useState } from 'react';
import { ProgressEvent } from '@/types';
import { getWebSocketUrl } from '@/lib/endpoints';
import { WSClient } from '@/lib/ws-client';

interface DocumentProgressHookState {
  events: ProgressEvent[];
  latestEvent: ProgressEvent | null;
  isConnected: boolean;
  error: string | null;
}

interface DocumentProgressStateInternal extends DocumentProgressHookState {
  sourceId: string | null;
}

const EMPTY_STATE: DocumentProgressStateInternal = {
  sourceId: null,
  events: [],
  latestEvent: null,
  isConnected: false,
  error: null,
};

/**
 * Hook for subscribing to real-time document progress events.
 * 
 * Automatically manages WebSocket connection lifecycle and reconnection.
 * Frontend should use REST API to recover state if WebSocket is down.
 */
export function useDocumentProgress(documentId: string | null) {
  const normalizedDocumentId =
    documentId && documentId !== 'undefined' && documentId !== 'null'
      ? documentId
      : null;
  const [state, setState] = useState<DocumentProgressStateInternal>(EMPTY_STATE);

  const wsClientRef = useRef<WSClient | null>(null);

  // Initialize and manage WebSocket connection
  useEffect(() => {
    if (!normalizedDocumentId) {
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
        sourceId: normalizedDocumentId,
        events: [...prev.events, event],
        latestEvent: event,
        error: null,
      }));
    };

    // Handle connection state changes
    const handleStateChange = (isConnected: boolean) => {
      setState((prev) => ({
        ...prev,
        sourceId: normalizedDocumentId,
        isConnected,
        error: isConnected ? null : 'WebSocket disconnected',
      }));
    };

    // Connect to WebSocket endpoint
    const url = getWebSocketUrl(`/ws/documents/${normalizedDocumentId}`);

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
  }, [normalizedDocumentId]);

  // Disconnect completely on component unmount
  useEffect(() => {
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
    };
  }, []);

  if (!normalizedDocumentId || state.sourceId !== normalizedDocumentId) {
    return {
      events: [],
      latestEvent: null,
      isConnected: false,
      error: null,
    } satisfies DocumentProgressHookState;
  }

  return {
    events: state.events,
    latestEvent: state.latestEvent,
    isConnected: state.isConnected,
    error: state.error,
  } satisfies DocumentProgressHookState;
}
