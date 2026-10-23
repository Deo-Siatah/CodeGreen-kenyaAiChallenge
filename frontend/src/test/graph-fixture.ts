import type { NetworkResponse } from '@/api/schemas';
import type { GraphEvent } from '@/domain/graph/types';

export const fixtureIds = {
  farmer: '11111111-1111-4111-8111-111111111111',
  farm: '22222222-2222-4222-8222-222222222222',
  trustSource: '33333333-3333-4333-8333-333333333333',
  marketActor: '44444444-4444-4444-8444-444444444444',
  socialGroup: '55555555-5555-4555-8555-555555555555',
  loan: '66666666-6666-4666-8666-666666666666',
  session: '77777777-7777-4777-8777-777777777777',
  trustParticipant: '88888888-8888-4888-8888-888888888888',
  marketParticipant: '99999999-9999-4999-8999-999999999999',
  socialParticipant: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
} as const;

const ids = fixtureIds;

/**
 * The live-flow events a user would have produced while building this farmer's
 * graph. Folding `eventsFromNetwork(networkPayload)` must yield the same node
 * and edge ids.
 */
export const liveFlowEvents: GraphEvent[] = [
  { type: 'FARMER_CREATED', farmerId: ids.farmer, label: 'Ann Wanjiku' },
  {
    type: 'FARM_CREATED',
    farmId: ids.farm,
    farmerId: ids.farmer,
    acreage: 2.5,
    latitude: -0.3,
    longitude: 36.1,
  },
  { type: 'VERIFIER_ADDED', verifierId: ids.trustSource, kind: 'trust_source', label: 'Chief Kariuki' },
  { type: 'VERIFIER_LINKED', farmerId: ids.farmer, verifierId: ids.trustSource, kind: 'trust_source' },
  { type: 'VERIFIER_ADDED', verifierId: ids.marketActor, kind: 'market_actor', label: 'Nakuru Grain' },
  { type: 'VERIFIER_LINKED', farmerId: ids.farmer, verifierId: ids.marketActor, kind: 'market_actor' },
  { type: 'VERIFIER_ADDED', verifierId: ids.socialGroup, kind: 'social_group', label: 'Mwangaza SACCO' },
  { type: 'VERIFIER_LINKED', farmerId: ids.farmer, verifierId: ids.socialGroup, kind: 'social_group' },
  { type: 'CREDIBILITY_UPDATED', verifierId: ids.trustSource, credibility: 0.9 },
  { type: 'CREDIBILITY_UPDATED', verifierId: ids.marketActor, credibility: 0.8 },
  {
    type: 'SESSION_STARTED',
    sessionId: ids.session,
    participants: [
      { participantId: ids.trustParticipant, verifierId: ids.trustSource },
      { participantId: ids.marketParticipant, verifierId: ids.marketActor },
      { participantId: ids.socialParticipant, verifierId: ids.socialGroup },
    ],
  },
  { type: 'PARTICIPANT_RESPONDED', participantId: ids.trustParticipant, rating: 4 },
  { type: 'PARTICIPANT_RESPONDED', participantId: ids.marketParticipant, rating: 3 },
  { type: 'PARTICIPANT_TIMED_OUT', participantId: ids.socialParticipant },
  {
    type: 'SCORE_COMPUTED',
    score: {
      final: 72,
      character: 70,
      capacity: 75,
      decision: 'ELIGIBLE',
      recommendedAmount: 3000,
    },
  },
  { type: 'LOAN_CREATED', loanId: ids.loan, amount: 3000 },
  { type: 'LOAN_DISBURSED', loanId: ids.loan },
];

export const networkPayload: NetworkResponse = {
  farmer: {
    id: ids.farmer,
    full_name: 'Ann Wanjiku',
    county: 'Nakuru',
  },
  farms: [
    {
      id: ids.farm,
      acreage: 2.5,
      latitude: -0.3,
      longitude: 36.1,
    },
  ],
  trust_sources: [
    {
      id: ids.trustSource,
      name: 'Chief Kariuki',
      category: 'local_leader',
      phone_masked: '0712*****678',
      credibility_score: 0.9,
    },
  ],
  market_actors: [
    {
      id: ids.marketActor,
      name: 'Nakuru Grain',
      actor_type: 'buyer',
      phone_masked: '0722*****123',
      credibility_score: 0.8,
    },
  ],
  social_groups: [
    {
      id: ids.socialGroup,
      name: 'Mwangaza SACCO',
      group_type: 'sacco',
    },
  ],
  latest_session: {
    id: ids.session,
    status: 'completed',
    participants: [
      {
        id: ids.trustParticipant,
        participant_type: 'trust_source',
        participant_id: ids.trustSource,
        responded: '2026-01-02T09:00:00Z',
      },
      {
        id: ids.marketParticipant,
        participant_type: 'market_actor',
        participant_id: ids.marketActor,
        responded: '2026-01-02T10:00:00Z',
      },
      {
        id: ids.socialParticipant,
        participant_type: 'social_group',
        participant_id: ids.socialGroup,
        responded: null,
      },
    ],
  },
  current_score: {
    id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    character_score: 70,
    capacity_score: 75,
    final_score: 72,
    decision: 'ELIGIBLE',
    recommended_amount: 3000,
  },
  loans: [
    {
      id: ids.loan,
      amount: 3000,
      status: 'disbursed',
      applied_at: '2026-01-03T09:00:00Z',
    },
  ],
};
