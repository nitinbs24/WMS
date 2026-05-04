import { useEffect, useRef, useCallback } from 'react';
import useWarehouseStore from '../store/useWarehouseStore';

/**
 * useWebSocket — Custom React Hook
 * 
 * Manages the persistent WebSocket connection to the FastAPI backend.
 * Routes incoming JSON events to the correct Zustand store action.
 * Implements exponential backoff reconnection on disconnect.
 * 
 * Usage:
 *   const { connectionStatus, sendMessage } = useWebSocket(url);
 */

const INITIAL_RETRY_DELAY = 500;   // ms
const MAX_RETRY_DELAY = 30000;     // ms
const BACKOFF_MULTIPLIER = 2;

// Event type → Zustand action mapping
const EVENT_HANDLERS = {
  BIN_UPDATED: (store, payload) => {
    store.updateBin(payload);
  },
  ORDER_PATH: (store, payload) => {
    store.setPath(payload.path || []);
    store.setPickSequence(payload.pick_sequence || []);
  },
  SLOTTING_SUGGESTION: (store, payload) => {
    store.addSlottingSuggestion(payload);
  },
  COLLISION_ERROR: (store, payload) => {
    store.addError({
      type: 'COLLISION',
      bin_id: payload.bin_id,
      message: payload.message || `Collision detected at bin ${payload.bin_id}`,
      timestamp: payload.timestamp,
    });
  },
  FULL_RESYNC: (store, payload) => {
    store.fullResync(payload);
  },
};

export default function useWebSocket(url) {
  const wsRef = useRef(null);
  const retryDelayRef = useRef(INITIAL_RETRY_DELAY);
  const retryTimeoutRef = useRef(null);
  const isMountedRef = useRef(true);

  const setConnectionStatus = useWarehouseStore((s) => s.setConnectionStatus);
  const connectionStatus = useWarehouseStore((s) => s.connectionStatus);

  const connect = useCallback(() => {
    if (!isMountedRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        console.log('[WS] Connected to', url);
        setConnectionStatus('connected');
        retryDelayRef.current = INITIAL_RETRY_DELAY; // reset backoff

        // Request resync with last known timestamp
        const lastTimestamp = useWarehouseStore.getState().lastTimestamp;
        if (lastTimestamp) {
          ws.send(JSON.stringify({
            type: 'RESYNC_REQUEST',
            last_timestamp: lastTimestamp,
          }));
          console.log('[WS] Sent RESYNC_REQUEST, last_timestamp:', lastTimestamp);
        }
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;

        try {
          const payload = JSON.parse(event.data);
          const eventType = payload.event;

          if (eventType && EVENT_HANDLERS[eventType]) {
            const store = useWarehouseStore.getState();
            EVENT_HANDLERS[eventType](store, payload);
          } else {
            console.warn('[WS] Unknown event type:', eventType, payload);
          }
        } catch (parseError) {
          console.error('[WS] Failed to parse message:', parseError);
        }
      };

      ws.onclose = (event) => {
        if (!isMountedRef.current) return;
        console.log('[WS] Disconnected. Code:', event.code, 'Reason:', event.reason);
        setConnectionStatus('disconnected');
        wsRef.current = null;
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WS] Error:', error);
        // onclose will fire after onerror — reconnection handled there
      };
    } catch (err) {
      console.error('[WS] Failed to create WebSocket:', err);
      setConnectionStatus('disconnected');
      scheduleReconnect();
    }
  }, [url, setConnectionStatus]);

  const scheduleReconnect = useCallback(() => {
    if (!isMountedRef.current) return;

    const delay = retryDelayRef.current;
    console.log(`[WS] Reconnecting in ${delay}ms...`);

    retryTimeoutRef.current = setTimeout(() => {
      retryDelayRef.current = Math.min(
        retryDelayRef.current * BACKOFF_MULTIPLIER,
        MAX_RETRY_DELAY
      );
      connect();
    }, delay);
  }, [connect]);

  const sendMessage = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WS] Cannot send — not connected');
    }
  }, []);

  const disconnect = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    setConnectionStatus('disconnected');
  }, [setConnectionStatus]);

  // Connect on mount, cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    connect();

    return () => {
      isMountedRef.current = false;
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmount');
        wsRef.current = null;
      }
    };
  }, [connect]);

  return {
    connectionStatus,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
}
