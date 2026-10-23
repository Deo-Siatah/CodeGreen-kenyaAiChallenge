import { describe, expect, it } from 'vitest';
import { graphReducer, initialState } from './reducer';
import type { GraphEvent, GraphState, Score } from './types';
import { liveFlowEvents } from '@/test/graph-fixture';

const FARMER = 'farmer-1';
const FARM = 'farm-1';
const TRUST = 'trust-1';
const MARKET = 'market-1';
const SOCIAL = 'social-1';
const SESSION = 'session-1';
const P_TRUST = 'p-trust';
const P_MARKET = 'p-market';
const P_SOCIAL = 'p-social';
const LOAN = 'loan-1';

const scoreA: Score = {
  final: 72,
  character: 70,
  capacity: 75,
  decision: 'ELIGIBLE',
  recommendedAmount: 3000,
};

const scoreB: Score = {
  final: 40,
  character: 38,
  capacity: null,
  decision: 'DECLINE',
  recommendedAmount: null,
};

function fold(events: GraphEvent[], from: GraphState = initialState): GraphState {
  return events.reduce((state, event) => graphReducer(state, event), from);
}

function edgesTouching(state: GraphState, nodeId: string) {
  return Object.values(state.edges).filter((edge) => edge.from === nodeId || edge.to === nodeId);
}

const assembled: GraphEvent[] = [
  { type: 'FARMER_CREATED', farmerId: FARMER, label: 'Ann' },
  { type: 'FARM_CREATED', farmId: FARM, farmerId: FARMER, acreage: 2 },
  { type: 'VERIFIER_ADDED', verifierId: TRUST, kind: 'trust_source', label: 'Chief' },
  { type: 'VERIFIER_LINKED', farmerId: FARMER, verifierId: TRUST, kind: 'trust_source' },
  { type: 'VERIFIER_ADDED', verifierId: MARKET, kind: 'market_actor', label: 'Buyer' },
  { type: 'VERIFIER_LINKED', farmerId: FARMER, verifierId: MARKET, kind: 'market_actor' },
  { type: 'VERIFIER_ADDED', verifierId: SOCIAL, kind: 'social_group', label: 'SACCO' },
  { type: 'VERIFIER_LINKED', farmerId: FARMER, verifierId: SOCIAL, kind: 'social_group' },
];

const verifying: GraphEvent[] = [
  ...assembled,
  {
    type: 'SESSION_STARTED',
    sessionId: SESSION,
    participants: [
      { participantId: P_TRUST, verifierId: TRUST },
      { participantId: P_MARKET, verifierId: MARKET },
      { participantId: P_SOCIAL, verifierId: SOCIAL },
    ],
  },
  { type: 'PARTICIPANT_RESPONDED', participantId: P_TRUST, rating: 4 },
  { type: 'PARTICIPANT_RESPONDED', participantId: P_MARKET, rating: 3 },
];

describe('graphReducer', () => {
  it('1. FARMER_CREATED creates one farmer node and moves phase to farmer', () => {
    const state = graphReducer(initialState, {
      type: 'FARMER_CREATED',
      farmerId: FARMER,
      label: 'Ann',
    });

    const nodes = Object.values(state.nodes);
    expect(nodes).toHaveLength(1);
    expect(nodes[0]?.kind).toBe('farmer');
    expect(nodes[0]?.id).toBe(FARMER);
    expect(state.phase).toBe('farmer');
  });

  it('2. FARM_CREATED adds a farm node and an owns edge', () => {
    const state = fold([
      { type: 'FARMER_CREATED', farmerId: FARMER, label: 'Ann' },
      { type: 'FARM_CREATED', farmId: FARM, farmerId: FARMER, acreage: 2 },
    ]);

    expect(state.nodes[FARM]?.kind).toBe('farm');
    expect(state.edges[`owns:${FARMER}->${FARM}`]?.kind).toBe('owns');
    expect(state.phase).toBe('farm');
  });

  it('3. VERIFIER_ADDED makes a ghost with no edge; VERIFIER_LINKED links and goes live', () => {
    const base = fold([
      { type: 'FARMER_CREATED', farmerId: FARMER, label: 'Ann' },
    ]);

    const ghost = graphReducer(base, {
      type: 'VERIFIER_ADDED',
      verifierId: TRUST,
      kind: 'trust_source',
      label: 'Chief',
    });

    expect(ghost.nodes[TRUST]?.state).toBe('ghost');
    expect(edgesTouching(ghost, TRUST)).toHaveLength(0);

    const linked = graphReducer(ghost, {
      type: 'VERIFIER_LINKED',
      farmerId: FARMER,
      verifierId: TRUST,
      kind: 'trust_source',
    });

    expect(linked.nodes[TRUST]?.state).toBe('live');
    expect(linked.edges[`vouches:${TRUST}->${FARMER}`]?.kind).toBe('vouches');
    expect(linked.phase).toBe('network');
  });

  it('4. SESSION_STARTED stores participants and sets verifiers pending', () => {
    const state = fold(verifying.slice(0, assembled.length + 1));

    expect(state.sessionId).toBe(SESSION);
    expect(state.participants[P_TRUST]).toBe(TRUST);
    expect(state.nodes[TRUST]?.state).toBe('pending');
    expect(state.nodes[MARKET]?.state).toBe('pending');
    expect(state.nodes[SOCIAL]?.state).toBe('pending');
    expect(state.phase).toBe('verifying');
  });

  it('5. PARTICIPANT_RESPONDED sets responded + rating; unknown id is ignored', () => {
    const state = fold(verifying);

    expect(state.nodes[TRUST]?.state).toBe('responded');
    expect(state.nodes[TRUST]?.rating).toBe(4);
    expect(state.nodes[MARKET]?.rating).toBe(3);

    const untouched = graphReducer(state, {
      type: 'PARTICIPANT_RESPONDED',
      participantId: 'does-not-exist',
      rating: 2,
    });

    expect(untouched).toEqual(state);
  });

  it('6. PARTICIPANT_TIMED_OUT sets timed_out', () => {
    const withSession = fold(verifying.slice(0, assembled.length + 1));
    const state = graphReducer(withSession, {
      type: 'PARTICIPANT_TIMED_OUT',
      participantId: P_SOCIAL,
    });

    expect(state.nodes[SOCIAL]?.state).toBe('timed_out');
  });

  it('7. SCORE_COMPUTED stores score, adds evidence edges, shifts previousScore', () => {
    const state = graphReducer(fold(verifying), { type: 'SCORE_COMPUTED', score: scoreA });

    expect(state.score).toEqual(scoreA);
    expect(state.previousScore).toBeNull();
    expect(state.edges[`evidence:${TRUST}->${FARMER}`]?.kind).toBe('evidence');
    expect(state.edges[`evidence:${MARKET}->${FARMER}`]?.kind).toBe('evidence');
    expect(state.edges[`evidence:${SOCIAL}->${FARMER}`]).toBeUndefined();
    expect(state.phase).toBe('scored');

    const rescored = graphReducer(state, { type: 'SCORE_COMPUTED', score: scoreB });
    expect(rescored.score).toEqual(scoreB);
    expect(rescored.previousScore).toEqual(scoreA);
  });

  it('8. LOAN_CREATED adds a loan + financed edge; resolution only marks meta', () => {
    const state = fold([
      { type: 'FARMER_CREATED', farmerId: FARMER, label: 'Ann' },
      { type: 'LOAN_CREATED', loanId: LOAN, amount: 3000 },
    ]);

    expect(state.nodes[LOAN]?.kind).toBe('loan');
    expect(state.edges[`financed:${FARMER}->${LOAN}`]?.kind).toBe('financed');
    expect(state.phase).toBe('financed');

    const resolved = graphReducer(state, {
      type: 'LOAN_RESOLVED',
      loanId: LOAN,
      outcome: 'defaulted',
    });

    expect(resolved.nodes[LOAN]).toBeDefined();
    expect(resolved.nodes[LOAN]?.meta.status).toBe('defaulted');
    expect(resolved.edges[`financed:${FARMER}->${LOAN}`]).toBeDefined();
  });

  it('9. CREDIBILITY_UPDATED sets credibility on the verifier node', () => {
    const state = fold(assembled);
    const updated = graphReducer(state, {
      type: 'CREDIBILITY_UPDATED',
      verifierId: TRUST,
      credibility: 0.9,
    });

    expect(updated.nodes[TRUST]?.credibility).toBe(0.9);
  });

  it('10. applying the same event twice is idempotent', () => {
    const once = fold(liveFlowEvents);
    const twice = liveFlowEvents.reduce(
      (state, event) => graphReducer(graphReducer(state, event), event),
      initialState,
    );

    expect(twice).toEqual(once);
    expect(Object.keys(twice.edges)).toHaveLength(Object.keys(once.edges).length);
  });

  it('11. the reducer never mutates its input', () => {
    const state = fold(verifying);
    const snapshot = JSON.parse(JSON.stringify(state)) as GraphState;

    graphReducer(state, { type: 'SCORE_COMPUTED', score: scoreA });

    expect(state).toEqual(snapshot);
  });
});
