import type { NetworkResponse } from '@/api/schemas';
import type { Decision, GraphEvent, Score, VerifierKind } from './types';

// Session statuses that mean the round is still open. Anything else means the
// window closed, so a participant without a response timestamp timed out.
const ACTIVE_SESSION_STATUSES = new Set(['pending', 'in_progress', 'active', 'started']);

function readString(source: Record<string, unknown>, key: string): string | null {
  const value = source[key];
  return typeof value === 'string' ? value : null;
}

function verifierKindOf(value: string): VerifierKind | null {
  if (value === 'trust_source' || value === 'market_actor' || value === 'social_group') {
    return value;
  }
  return null;
}

function isDecision(value: string | null | undefined): value is Decision {
  return value === 'ELIGIBLE' || value === 'REVIEW_REQUIRED' || value === 'DECLINE';
}

function toScore(score: NetworkResponse['current_score']): Score | null {
  if (!score) {
    return null;
  }
  if (
    typeof score.final_score !== 'number' ||
    typeof score.character_score !== 'number' ||
    !isDecision(score.decision)
  ) {
    return null;
  }
  return {
    final: score.final_score,
    character: score.character_score,
    capacity: score.capacity_score ?? null,
    decision: score.decision,
    recommendedAmount: score.recommended_amount ?? null,
  };
}

export function eventsFromNetwork(network: NetworkResponse): GraphEvent[] {
  const events: GraphEvent[] = [];

  const farmerId = readString(network.farmer, 'id');
  if (!farmerId) {
    return events;
  }

  events.push({
    type: 'FARMER_CREATED',
    farmerId,
    label: readString(network.farmer, 'full_name') ?? 'Farmer',
  });

  for (const farm of network.farms) {
    events.push({
      type: 'FARM_CREATED',
      farmId: farm.id,
      farmerId,
      acreage: farm.acreage,
      latitude: farm.latitude,
      longitude: farm.longitude,
    });
  }

  const added = new Set<string>();

  for (const source of network.trust_sources) {
    events.push({
      type: 'VERIFIER_ADDED',
      verifierId: source.id,
      kind: 'trust_source',
      label: source.name,
    });
    events.push({
      type: 'VERIFIER_LINKED',
      farmerId,
      verifierId: source.id,
      kind: 'trust_source',
    });
    events.push({
      type: 'CREDIBILITY_UPDATED',
      verifierId: source.id,
      credibility: source.credibility_score,
    });
    added.add(source.id);
  }

  for (const actor of network.market_actors) {
    events.push({
      type: 'VERIFIER_ADDED',
      verifierId: actor.id,
      kind: 'market_actor',
      label: actor.name,
    });
    events.push({
      type: 'VERIFIER_LINKED',
      farmerId,
      verifierId: actor.id,
      kind: 'market_actor',
    });
    events.push({
      type: 'CREDIBILITY_UPDATED',
      verifierId: actor.id,
      credibility: actor.credibility_score,
    });
    added.add(actor.id);
  }

  for (const group of network.social_groups) {
    events.push({
      type: 'VERIFIER_ADDED',
      verifierId: group.id,
      kind: 'social_group',
      label: group.name,
    });
    events.push({
      type: 'VERIFIER_LINKED',
      farmerId,
      verifierId: group.id,
      kind: 'social_group',
    });
    added.add(group.id);
  }

  const session = network.latest_session;
  if (session) {
    for (const participant of session.participants) {
      const kind = verifierKindOf(participant.participant_type);
      if (kind && !added.has(participant.participant_id)) {
        events.push({
          type: 'VERIFIER_ADDED',
          verifierId: participant.participant_id,
          kind,
          label: 'Verifier',
        });
        events.push({
          type: 'VERIFIER_LINKED',
          farmerId,
          verifierId: participant.participant_id,
          kind,
        });
        added.add(participant.participant_id);
      }
    }

    events.push({
      type: 'SESSION_STARTED',
      sessionId: session.id,
      participants: session.participants.map((participant) => ({
        participantId: participant.id,
        verifierId: participant.participant_id,
      })),
    });

    const sessionActive = ACTIVE_SESSION_STATUSES.has(session.status);
    for (const participant of session.participants) {
      if (participant.responded) {
        events.push({ type: 'PARTICIPANT_RESPONDED', participantId: participant.id });
      } else if (!sessionActive) {
        events.push({ type: 'PARTICIPANT_TIMED_OUT', participantId: participant.id });
      }
    }
  }

  const score = toScore(network.current_score);
  if (score) {
    events.push({ type: 'SCORE_COMPUTED', score });
  }

  for (const loan of network.loans) {
    events.push({ type: 'LOAN_CREATED', loanId: loan.id, amount: loan.amount ?? 0 });
    if (loan.status === 'disbursed') {
      events.push({ type: 'LOAN_DISBURSED', loanId: loan.id });
    } else if (loan.status === 'repaid' || loan.status === 'defaulted') {
      events.push({ type: 'LOAN_RESOLVED', loanId: loan.id, outcome: loan.status });
    }
  }

  return events;
}
