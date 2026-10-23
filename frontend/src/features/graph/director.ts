import type { GraphEvent } from '@/domain/graph';

export const BEAT_MS: Record<GraphEvent['type'], number> = {
  FARMER_CREATED: 1200,
  FARM_CREATED: 1000,
  VERIFIER_ADDED: 500,
  VERIFIER_LINKED: 700,
  SESSION_STARTED: 1400,
  PARTICIPANT_RESPONDED: 900,
  PARTICIPANT_TIMED_OUT: 600,
  SCORE_COMPUTED: 2400,
  LOAN_CREATED: 900,
  LOAN_DISBURSED: 900,
  LOAN_RESOLVED: 900,
  CREDIBILITY_UPDATED: 500,
  GRAPH_HYDRATED: 1800,
};

export function beatDuration(event: GraphEvent): number {
  return BEAT_MS[event.type];
}

export interface Director {
  enqueue(events: GraphEvent[]): Promise<void>;
  cancel(): void;
}

export interface DirectorOptions {
  apply: (event: GraphEvent) => void;
  wait: (ms: number) => Promise<void>;
  instant: boolean;
}

export function createDirector(options: DirectorOptions): Director {
  const cancelListeners = new Set<() => void>();
  let cancelled = false;

  function pause(ms: number): Promise<void> {
    if (options.instant || ms <= 0) {
      return Promise.resolve();
    }
    let release: (() => void) | null = null;
    const cancellation = new Promise<void>((resolve) => {
      release = resolve;
    });
    if (release) {
      cancelListeners.add(release);
    }
    return Promise.race([options.wait(ms), cancellation]).finally(() => {
      if (release) {
        cancelListeners.delete(release);
      }
    });
  }

  async function enqueue(events: GraphEvent[]): Promise<void> {
    cancelled = false;

    if (options.instant) {
      for (const event of events) {
        if (cancelled) {
          break;
        }
        options.apply(event);
      }
      return;
    }

    for (const event of events) {
      if (cancelled) {
        break;
      }
      options.apply(event);
      await pause(beatDuration(event));
    }
  }

  function cancel(): void {
    cancelled = true;
    for (const release of cancelListeners) {
      release();
    }
    cancelListeners.clear();
  }

  return { enqueue, cancel };
}
