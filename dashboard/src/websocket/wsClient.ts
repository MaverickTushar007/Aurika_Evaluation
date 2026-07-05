import { useWorldStore } from '../state/useWorldStore';

class AurikaWebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectInterval: number = 3000;
  private mockInterval: number | null = null;
  private isConnected: boolean = false;

  constructor(url: string = 'ws://localhost:8000/ws') {
    this.url = url;
  }

  public connect(): void {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[AIP WebSocket] Connected to real-time enterprise stream.');
        this.isConnected = true;
        useWorldStore.getState().setWsConnected(true);
        if (this.mockInterval) {
          clearInterval(this.mockInterval);
          this.mockInterval = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleEvent(payload);
        } catch (err) {
          console.error('[AIP WebSocket] Parse error:', err);
        }
      };

      this.ws.onclose = () => {
        console.warn('[AIP WebSocket] Connection closed. Attempting reconnect & starting simulation fallback...');
        this.isConnected = false;
        useWorldStore.getState().setWsConnected(false);
        this.startMockFallback();
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      this.startMockFallback();
      setTimeout(() => this.connect(), this.reconnectInterval);
    }
  }

  private handleEvent(payload: any): void {
    const store = useWorldStore.getState();
    if (payload.topic === 'TableOccupied') {
      store.updateTable(payload.tableId, 'OCCUPIED', payload.guests);
    } else if (payload.topic === 'TableAvailable') {
      store.updateTable(payload.tableId, 'AVAILABLE', 0);
    } else if (payload.topic === 'KPIUpdate') {
      store.updateKPIs(payload.data);
    } else if (payload.topic === 'AlertRaised') {
      store.addAlert(payload.alert);
    }
  }

  private startMockFallback(): void {
    // Disable client-side mock simulation loops in production
    const isProduction = (import.meta as any).env?.PROD || window.location.hostname !== 'localhost';
    if (isProduction) {
      console.warn('[AIP WebSocket] Running in production mode. Local simulation fallback is disabled.');
      return;
    }

    if (this.mockInterval) return;
    console.log('[AIP WebSocket] Running local live simulation engine...');
    
    this.mockInterval = window.setInterval(() => {
      const store = useWorldStore.getState();
      const currentKpis = store.kpis;

      // Simulate live fluctuations
      const fpsJitter = +(29.5 + Math.random() * 1.2 - 0.6).toFixed(1);
      const queueDelta = Math.random() > 0.7 ? (Math.random() > 0.5 ? 1 : -1) : 0;
      const newQueue = Math.max(0, Math.min(15, currentKpis.queueLength + queueDelta));
      const newWait = Math.max(0, newQueue * 2.5);

      store.updateKPIs({
        inferenceFps: fpsJitter,
        queueLength: newQueue,
        expectedWaitMinutes: Math.round(newWait),
      });

      // Occasionally toggle table status
      if (Math.random() > 0.85) {
        const tables = store.tables;
        const randomTable = tables[Math.floor(Math.random() * tables.length)];
        const nextStatus = randomTable.status === 'AVAILABLE' ? 'OCCUPIED' : 'AVAILABLE';
        store.updateTable(randomTable.id, nextStatus, nextStatus === 'OCCUPIED' ? randomTable.capacity : 0);
      }
    }, 3500);
  }

  public disconnect(): void {
    if (this.mockInterval) clearInterval(this.mockInterval);
    if (this.ws) this.ws.close();
  }
}

export const wsClient = new AurikaWebSocketClient();
