import { describe, expect, it } from 'vitest';
import { graphReducer, initialState, type GraphEvent } from '@/domain/graph';
import { defaultReplay, parseReplay, replayEvents } from './index';

function fold(events: GraphEvent[]) {
  return events.reduce((state, event) => graphReducer(state, event), initialState);
}

describe('recorded replay', () => {
  it('labels the recording and keeps its real backend source', () => {
    expect(defaultReplay.version).toBe(1);
    expect(defaultReplay.label).toContain('Grace Wanjiku');
    expect(defaultReplay.source).toContain('/api/farmers/');
    expect(defaultReplay.recordedAt).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(defaultReplay.farmer_id).toBe(defaultReplay.network.farmer.id);
  });

  it('turns the recorded network into a complete graph event log', () => {
    const events = replayEvents(defaultReplay);
    const state = fold(events);

    expect(state.nodes[defaultReplay.farmer_id]?.label).toBe('Grace Wanjiku');
    expect(state.phase).toBe('financed');

    const loan = Object.values(state.nodes).find((node) => node.kind === 'loan');
    expect(loan?.meta.status).toBe('repaid');
    expect(events.some((event) => event.type === 'SCORE_COMPUTED')).toBe(true);
  });

  it('rejects a recording without a source label', () => {
    expect(() => parseReplay({ ...defaultReplay, source: '' })).toThrow(/source/i);
  });
});
