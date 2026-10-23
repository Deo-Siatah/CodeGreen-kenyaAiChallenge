import { describe, expect, it } from 'vitest';
import { graphReducer, initialState } from './reducer';
import { allResponded, edgesOf, respondedCount, verifierIds, visibleNodes } from './selectors';
import type { GraphEvent, GraphState } from './types';

const FARMER = 'farmer-1';
const FARM = 'farm-1';
const TRUST = 'trust-1';
const MARKET = 'market-1';
const P_TRUST = 'p-trust';
const P_MARKET = 'p-market';

function fold(events: GraphEvent[]): GraphState {
  return events.reduce((state, event) => graphReducer(state, event), initialState);
}

const events: GraphEvent[] = [
  { type: 'FARMER_CREATED', farmerId: FARMER, label: 'Ann' },
  { type: 'FARM_CREATED', farmId: FARM, farmerId: FARMER, acreage: 2 },
  { type: 'VERIFIER_ADDED', verifierId: TRUST, kind: 'trust_source', label: 'Chief' },
  { type: 'VERIFIER_LINKED', farmerId: FARMER, verifierId: TRUST, kind: 'trust_source' },
  { type: 'VERIFIER_ADDED', verifierId: MARKET, kind: 'market_actor', label: 'Buyer' },
  { type: 'VERIFIER_LINKED', farmerId: FARMER, verifierId: MARKET, kind: 'market_actor' },
  {
    type: 'SESSION_STARTED',
    sessionId: 'session-1',
    participants: [
      { participantId: P_TRUST, verifierId: TRUST },
      { participantId: P_MARKET, verifierId: MARKET },
    ],
  },
];

describe('selectors', () => {
  it('visibleNodes returns every node in a deterministic order', () => {
    const state = fold(events);
    const kinds = visibleNodes(state).map((node) => node.kind);

    expect(visibleNodes(state)).toEqual(visibleNodes(state));
    expect(kinds).toEqual(['farmer', 'farm', 'trust_source', 'market_actor']);
  });

  it('edgesOf returns edges touching a node', () => {
    const state = fold(events);
    const ids = edgesOf(state, TRUST).map((edge) => edge.id).sort();

    expect(ids).toEqual([`vouches:${TRUST}->${FARMER}`]);
    expect(edgesOf(state, FARMER)).toHaveLength(3);
  });

  it('respondedCount and allResponded reflect participant state', () => {
    const base = fold(events);
    expect(respondedCount(base)).toBe(0);
    expect(allResponded(base)).toBe(false);

    const one = graphReducer(base, { type: 'PARTICIPANT_RESPONDED', participantId: P_TRUST });
    expect(respondedCount(one)).toBe(1);
    expect(allResponded(one)).toBe(false);

    const two = graphReducer(one, { type: 'PARTICIPANT_RESPONDED', participantId: P_MARKET });
    expect(respondedCount(two)).toBe(2);
    expect(allResponded(two)).toBe(true);
  });

  it('allResponded is false when there is no session', () => {
    expect(allResponded(initialState)).toBe(false);
  });

  it('verifierIds returns only verifier nodes', () => {
    const state = fold(events);
    expect(verifierIds(state).sort()).toEqual([MARKET, TRUST]);
  });
});
