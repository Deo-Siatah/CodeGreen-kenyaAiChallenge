import { create } from 'zustand';

export interface RequestLogEntry {
  id: number;
  at: number;
  method: string;
  path: string;
  status: number | null;
  durationMs: number;
  ok: boolean;
}

interface RequestLogState {
  entries: RequestLogEntry[];
  record: (entry: Omit<RequestLogEntry, 'id'>) => void;
  clear: () => void;
}

let nextId = 1;

// The evidence ledger: every API call made during a case, in order. The client
// interceptors write here; the UI only reads.
export const useRequestLog = create<RequestLogState>()((set) => ({
  entries: [],
  record: (entry) =>
    set((state) => ({ entries: [...state.entries, { id: (nextId += 1), ...entry }] })),
  clear: () => set({ entries: [] }),
}));

export function recordRequest(entry: Omit<RequestLogEntry, 'id'>): void {
  useRequestLog.getState().record(entry);
}

export function clearRequestLog(): void {
  useRequestLog.getState().clear();
}
