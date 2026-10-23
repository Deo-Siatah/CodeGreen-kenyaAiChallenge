import { create } from 'zustand';
import { graphReducer, initialState, type GraphEvent, type GraphState } from '@/domain/graph';
import { createDirector, type Director } from './director';

export interface Pulse {
  id: string;
  from: string;
  to: string;
  kind: 'out' | 'back';
}

export interface GraphStoreState extends GraphState {
  log: GraphEvent[];
  pulses: Pulse[];
  playing: boolean;
  instant: boolean;
  dispatch: (events: GraphEvent[], options?: { instant?: boolean }) => Promise<void>;
  reset: () => void;
  cancel: () => void;
}

export const PULSE_MS = 1300;

function defaultWait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findFarmerId(state: GraphState): string | null {
  const farmer = Object.values(state.nodes).find((node) => node.kind === 'farmer');
  return farmer ? farmer.id : null;
}

function pulsesFor(event: GraphEvent, state: GraphState): Pulse[] {
  const farmerId = findFarmerId(state);
  if (!farmerId) {
    return [];
  }

  if (event.type === 'SESSION_STARTED') {
    return event.participants.map((participant) => ({
      id: `pulse-${event.sessionId}-${participant.participantId}`,
      from: farmerId,
      to: participant.verifierId,
      kind: 'out' as const,
    }));
  }

  if (event.type === 'PARTICIPANT_RESPONDED') {
    const verifierId = state.participants[event.participantId];
    if (!verifierId) {
      return [];
    }
    return [
      {
        id: `pulse-${event.participantId}-back`,
        from: verifierId,
        to: farmerId,
        kind: 'back' as const,
      },
    ];
  }

  return [];
}

export const useGraphStore = create<GraphStoreState>()((set, get) => {
  let active: Director | null = null;

  function apply(event: GraphEvent): void {
    const created = pulsesFor(event, get());
    set((state) => ({
      ...graphReducer(state, event),
      log: [...state.log, event],
      pulses: [...state.pulses, ...created],
    }));

    if (created.length > 0 && !get().instant) {
      const ids = new Set(created.map((pulse) => pulse.id));
      setTimeout(() => {
        set((state) => ({ pulses: state.pulses.filter((pulse) => !ids.has(pulse.id)) }));
      }, PULSE_MS);
    }
  }

  return {
    ...initialState,
    log: [],
    pulses: [],
    playing: false,
    instant: false,

    dispatch: async (events, options) => {
      active?.cancel();
      const instant = options?.instant ?? get().instant;
      set({ instant });
      const director = createDirector({ apply, wait: defaultWait, instant });
      active = director;
      set({ playing: true });
      try {
        await director.enqueue(events);
      } finally {
        if (active === director) {
          active = null;
          set({ playing: false });
        }
      }
    },

    reset: () => {
      active?.cancel();
      active = null;
      set({ ...initialState, log: [], pulses: [], playing: false });
    },

    cancel: () => {
      active?.cancel();
      active = null;
      set({ playing: false });
    },
  };
});
