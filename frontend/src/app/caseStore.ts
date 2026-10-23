import { create } from 'zustand';

export type CaseStatus = 'idle' | 'hydrating' | 'ready' | 'not_found' | 'error';

export const STEP_COUNT = 6;

interface CaseState {
  caseId: string | null;
  status: CaseStatus;
  error: string | null;
  step: number;
  setStep: (step: number) => void;
  beginCase: (caseId: string) => void;
  setStatus: (status: CaseStatus, error?: string | null) => void;
  reset: () => void;
}

export const useCaseStore = create<CaseState>()((set) => ({
  caseId: null,
  status: 'idle',
  error: null,
  step: 1,
  setStep: (step) => set({ step }),
  beginCase: (caseId) => set({ caseId, status: 'hydrating', error: null, step: 1 }),
  setStatus: (status, error = null) => set({ status, error }),
  reset: () => set({ caseId: null, status: 'idle', error: null, step: 1 }),
}));
