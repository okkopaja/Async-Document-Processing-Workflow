import { ProgressEvent } from '@/types';

export type MessageHandler = (event: ProgressEvent) => void;
export type StateChangeHandler = (isConnected: boolean) => void;

interface ConnectionConfig {
  maxRetries?: number;
  initialDelayMs?: number;
  maxDelayMs?: number;
}

/**
 * WebSocket client with auto-reconnect, state tracking, and error handling.
 * Follows exponential backoff strategy for reconnection attempts.
 */
export class WSClient {
  private ws: WebSocket | null = null;
  private url: string = '';
  private messageHandlers: Set<MessageHandler> = new Set();
  private stateChangeHandlers: Set<StateChangeHandler> = new Set();
  
  // Reconnection state
  private reconnectTimer: number | null = null;
  private reconnectAttempts: number = 0;
  private readonly maxRetries: number;
  private readonly initialDelayMs: number;
  private readonly maxDelayMs: number;
  private isIntentionallyClosed: boolean = false;

  constructor(config: ConnectionConfig = {}) {
    this.maxRetries = config.maxRetries ?? 10;
    this.initialDelayMs = config.initialDelayMs ?? 1000;
    this.maxDelayMs = config.maxDelayMs ?? 30000;
  }

  /**
   * Connect to a WebSocket URL.
   * Automatically handles reconnection on disconnect.
   */
  connect(url: string, onMessage?: MessageHandler): void {
    if (onMessage) {
      this.messageHandlers.add(onMessage);
    }

    const hasActiveSocket =
      this.ws !== null &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING);

    if (hasActiveSocket && this.url === url) {
      return;
    }

    if (hasActiveSocket) {
      this.disconnect();
    }

    this.url = url;
    this.isIntentionallyClosed = false;

    this._connect();
  }

  /**
   * Register a handler for progress messages.
   */
  onMessage(handler: MessageHandler): void {
    this.messageHandlers.add(handler);
  }

  /**
   * Register a handler for connection state changes.
   */
  onStateChange(handler: StateChangeHandler): void {
    this.stateChangeHandlers.add(handler);
  }

  /**
   * Unregister a message handler.
   */
  offMessage(handler: MessageHandler): void {
    this.messageHandlers.delete(handler);
  }

  /**
   * Unregister a state change handler.
   */
  offStateChange(handler: StateChangeHandler): void {
    this.stateChangeHandlers.delete(handler);
  }

  /**
   * Gracefully disconnect and prevent reconnection.
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;
    this._clearReconnectTimer();
    
    if (this.ws) {
      const activeSocket = this.ws;
      this.ws = null;

      // Avoid browser "closed before established" noise in development.
      if (activeSocket.readyState === WebSocket.CONNECTING) {
        activeSocket.onopen = () => {
          activeSocket.close();
        };
      } else if (activeSocket.readyState === WebSocket.OPEN) {
        activeSocket.close();
      }
    }
    
    this._notifyStateChange(false);
  }

  /**
   * Check if currently connected.
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Internal: Establish the WebSocket connection.
   */
  private _connect(): void {
    if (this.isConnected()) {
      return;
    }

    try {
      const ws = new WebSocket(this.url);
      this.ws = ws;

      ws.onopen = () => {
        if (this.ws !== ws) {
          return;
        }
        console.log(`[WSClient] Connected to ${this.url}`);
        this.reconnectAttempts = 0;
        this._notifyStateChange(true);
      };

      ws.onmessage = (event) => {
        if (this.ws !== ws) {
          return;
        }
        try {
          const parsed = JSON.parse(event.data as string) as ProgressEvent;
          this.messageHandlers.forEach((handler) => handler(parsed));
        } catch (error) {
          console.error('[WSClient] Failed to parse message:', event.data, error);
        }
      };

      ws.onerror = (error) => {
        if (this.ws !== ws || this.isIntentionallyClosed) {
          return;
        }
        console.error(`[WSClient] WebSocket error on ${this.url}:`, error);
      };

      ws.onclose = () => {
        if (this.ws !== ws) {
          return;
        }
        console.log(`[WSClient] Connection closed to ${this.url}`);
        this.ws = null;
        this._notifyStateChange(false);

        // Auto-reconnect if not intentionally closed
        if (!this.isIntentionallyClosed) {
          this._scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('[WSClient] Failed to create WebSocket:', error);
      this._notifyStateChange(false);
      
      if (!this.isIntentionallyClosed) {
        this._scheduleReconnect();
      }
    }
  }

  /**
   * Schedule a reconnection attempt with exponential backoff.
   */
  private _scheduleReconnect(): void {
    if (this.isIntentionallyClosed || this.reconnectAttempts >= this.maxRetries) {
      console.warn(
        `[WSClient] Max reconnection attempts reached (${this.reconnectAttempts}/${this.maxRetries})`
      );
      return;
    }

    this._clearReconnectTimer();

    // Exponential backoff with jitter
    const delayMs = Math.min(
      this.initialDelayMs * Math.pow(2, this.reconnectAttempts) +
      Math.random() * 1000,
      this.maxDelayMs
    );

    console.log(
      `[WSClient] Scheduling reconnect in ${Math.round(delayMs)}ms (attempt ${this.reconnectAttempts + 1}/${this.maxRetries})`
    );

    this.reconnectAttempts += 1;
    this.reconnectTimer = window.setTimeout(() => {
      console.log(`[WSClient] Attempting reconnect (${this.reconnectAttempts}/${this.maxRetries})`);
      this._connect();
    }, delayMs);
  }

  /**
   * Clear any pending reconnect timer.
   */
  private _clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Notify all state change handlers.
   */
  private _notifyStateChange(isConnected: boolean): void {
    this.stateChangeHandlers.forEach((handler) => {
      try {
        handler(isConnected);
      } catch (error) {
        console.error('[WSClient] Error in state change handler:', error);
      }
    });
  }
}
