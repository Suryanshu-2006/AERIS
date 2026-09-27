import { SystemState, WhatIfResult } from '../types';

const API_BASE = 'http://localhost:8000/api';
const WS_BASE = 'ws://localhost:8000/ws/telemetry';

export class AerisApiService {
  private ws: WebSocket | null = null;
  private onStateCallback: ((state: SystemState) => void) | null = null;
  private reconnectTimer: any = null;

  connectWebSocket(onState: (state: SystemState) => void) {
    this.onStateCallback = onState;
    if (this.ws) {
      try { this.ws.close(); } catch (_) {}
    }

    try {
      this.ws = new WebSocket(WS_BASE);
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onStateCallback) {
            this.onStateCallback(data);
          }
        } catch (e) {
          console.error("WS Parse error:", e);
        }
      };

      this.ws.onerror = () => {
        // Fallback or retry
      };

      this.ws.onclose = () => {
        this.reconnectTimer = setTimeout(() => {
          this.connectWebSocket(onState);
        }, 2000);
      };
    } catch (e) {
      console.warn("WebSocket init error, will fallback to polling", e);
    }
  }

  disconnectWebSocket() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  async fetchState(): Promise<SystemState | null> {
    try {
      let res = await fetch(`${API_BASE}/state`);
      if (!res.ok) res = await fetch(`${API_BASE}/telemetry/state`);
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  async startSimulation(): Promise<boolean> {
    try {
      let res = await fetch(`${API_BASE}/simulation/start`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${API_BASE}/sim/start`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async pauseSimulation(): Promise<boolean> {
    try {
      let res = await fetch(`${API_BASE}/simulation/pause`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${API_BASE}/sim/pause`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async resumeSimulation(): Promise<boolean> {
    try {
      let res = await fetch(`${API_BASE}/simulation/resume`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${API_BASE}/sim/resume`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async resetSimulation(): Promise<boolean> {
    try {
      let res = await fetch(`${API_BASE}/simulation/reset`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${API_BASE}/sim/reset`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async setSpeed(speed: number): Promise<boolean> {
    try {
      const payload = JSON.stringify({ speed });
      let res = await fetch(`${API_BASE}/simulation/speed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
      });
      if (!res.ok) {
        res = await fetch(`${API_BASE}/sim/speed`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
        });
      }
      return res.ok;
    } catch {
      return false;
    }
  }

  async injectFault(fault_id: string, severity = 0.5): Promise<boolean> {
    try {
      const payload = JSON.stringify({ fault_id, severity });
      let res = await fetch(`${API_BASE}/fault/inject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
      });
      if (!res.ok) {
        res = await fetch(`${API_BASE}/faults/inject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
        });
      }
      return res.ok;
    } catch {
      return false;
    }
  }

  async clearFaults(): Promise<boolean> {
    try {
      let res = await fetch(`${API_BASE}/fault/clear-all`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${API_BASE}/faults/clear-all`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  }

  async runWhatIf(params: {
    altitude_ft?: number;
    ambient_temperature_c?: number;
    loiter_duration_minutes?: number;
    throttle_percent?: number;
  }): Promise<WhatIfResult | null> {
    try {
      const payload = JSON.stringify(params);
      let res = await fetch(`${API_BASE}/mission/what-if`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
      });
      if (!res.ok) {
        res = await fetch(`${API_BASE}/missions/what-if`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
        });
      }
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  async loadScenario(scenario_id: string): Promise<boolean> {
    try {
      let res = await fetch(`${API_BASE}/simulation/scenario/${scenario_id}`, { method: 'POST' });
      if (!res.ok) res = await fetch(`${API_BASE}/sim/scenario/${scenario_id}`, { method: 'POST' });
      return res.ok;
    } catch {
      return false;
    }
  }
}

export const api = new AerisApiService();
