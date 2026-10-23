import { describe, expect, it } from 'vitest';
import { graphReducer, initialState } from './reducer';
import { eventsFromNetwork } from './hydrate';
import type { GraphEvent, GraphState } from './types';
import { liveFlowEvents, networkPayload } from '@/test/graph-fixture';

function fold(events: GraphEvent[]): GraphState {
  return events.reduce((state, event) => graphReducer(state, event), initialState);
}

function sortedKeys(record: Record<string, unknown>): string[] {
  return Object.keys(record).sort();
}

describe('eventsFromNetwork', () => {
  it('12. folding the recorded events is deterministic and serialisable', () => {
    const first = fold(liveFlowEvents);
    const second = fold(liveFlowEvents);

    expect(second).toEqual(first);
    expect(() => JSON.stringify(first)).not.toThrow();
    expect(JSON.parse(JSON.stringify(first))).toEqual(first);
  });

  it('13. hydrate reproduces the same node and edge ids as the live flow', () => {
    const live = fold(liveFlowEvents);
    const hydrated = fold(eventsFromNetwork(networkPayload));

    expect(sortedKeys(hydrated.nodes)).toEqual(sortedKeys(live.nodes));
    expect(sortedKeys(hydrated.edges)).toEqual(sortedKeys(live.edges));
  });
});
