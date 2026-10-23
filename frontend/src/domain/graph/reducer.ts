import type {
  GraphEdge,
  GraphEvent,
  GraphNode,
  GraphState,
  MetaValue,
  Phase,
  Score,
  VerifierKind,
} from './types';

export const initialState: GraphState = {
  nodes: {},
  edges: {},
  phase: 'empty',
  participants: {},
  sessionId: null,
  score: null,
  previousScore: null,
};

const PHASE_RANK: Record<Phase, number> = {
  empty: 0,
  farmer: 1,
  farm: 2,
  network: 3,
  verifying: 4,
  scored: 5,
  financed: 6,
};

function advancePhase(current: Phase, next: Phase): Phase {
  return PHASE_RANK[next] > PHASE_RANK[current] ? next : current;
}

export function edgeId(from: string, to: string, kind: GraphEdge['kind']): string {
  return `${kind}:${from}->${to}`;
}

function linkEdge(farmerId: string, verifierId: string, kind: VerifierKind): GraphEdge {
  if (kind === 'social_group') {
    return {
      id: edgeId(farmerId, verifierId, 'member_of'),
      from: farmerId,
      to: verifierId,
      kind: 'member_of',
    };
  }
  const edgeKind = kind === 'trust_source' ? 'vouches' : 'buys_from';
  return {
    id: edgeId(verifierId, farmerId, edgeKind),
    from: verifierId,
    to: farmerId,
    kind: edgeKind,
  };
}

function withNode(state: GraphState, node: GraphNode): GraphState {
  if (state.nodes[node.id] === node) {
    return state;
  }
  return { ...state, nodes: { ...state.nodes, [node.id]: node } };
}

function withEdge(state: GraphState, edge: GraphEdge): GraphState {
  if (state.edges[edge.id]) {
    return state;
  }
  return { ...state, edges: { ...state.edges, [edge.id]: edge } };
}

function patchNode(state: GraphState, nodeId: string, patch: Partial<GraphNode>): GraphState {
  const existing = state.nodes[nodeId];
  if (!existing) {
    return state;
  }
  return withNode(state, { ...existing, ...patch });
}

function findFarmerId(state: GraphState): string | null {
  const farmer = Object.values(state.nodes).find((node) => node.kind === 'farmer');
  return farmer ? farmer.id : null;
}

function scoresEqual(a: Score, b: Score): boolean {
  return (
    a.final === b.final &&
    a.character === b.character &&
    a.capacity === b.capacity &&
    a.decision === b.decision &&
    a.recommendedAmount === b.recommendedAmount
  );
}

function numberOrNull(value: number | null | undefined): MetaValue {
  return value === undefined || value === null ? null : value;
}

function isSettled(state: GraphState, nodeId: string): boolean {
  const node = state.nodes[nodeId];
  return node?.state === 'responded' || node?.state === 'timed_out';
}

export function graphReducer(state: GraphState, event: GraphEvent): GraphState {
  switch (event.type) {
    case 'FARMER_CREATED': {
      let next = state;
      if (!next.nodes[event.farmerId]) {
        next = withNode(next, {
          id: event.farmerId,
          kind: 'farmer',
          label: event.label,
          state: 'live',
          meta: {},
        });
      }
      return { ...next, phase: advancePhase(next.phase, 'farmer') };
    }

    case 'FARM_CREATED': {
      let next = state;
      if (!next.nodes[event.farmId]) {
        next = withNode(next, {
          id: event.farmId,
          kind: 'farm',
          label: event.label ?? 'Farm',
          state: 'live',
          meta: {
            acreage: numberOrNull(event.acreage),
            latitude: numberOrNull(event.latitude),
            longitude: numberOrNull(event.longitude),
          },
        });
      }
      next = withEdge(next, {
        id: edgeId(event.farmerId, event.farmId, 'owns'),
        from: event.farmerId,
        to: event.farmId,
        kind: 'owns',
      });
      return { ...next, phase: advancePhase(next.phase, 'farm') };
    }

    case 'VERIFIER_ADDED': {
      if (state.nodes[event.verifierId]) {
        return state;
      }
      return withNode(state, {
        id: event.verifierId,
        kind: event.kind,
        label: event.label,
        state: 'ghost',
        meta: {},
      });
    }

    case 'VERIFIER_LINKED': {
      let next = state;
      if (!next.nodes[event.verifierId]) {
        next = withNode(next, {
          id: event.verifierId,
          kind: event.kind,
          label: 'Verifier',
          state: 'live',
          meta: {},
        });
      } else if (!isSettled(next, event.verifierId)) {
        next = patchNode(next, event.verifierId, { state: 'live' });
      }
      next = withEdge(next, linkEdge(event.farmerId, event.verifierId, event.kind));
      return { ...next, phase: advancePhase(next.phase, 'network') };
    }

    case 'SESSION_STARTED': {
      const participants: Record<string, string> = { ...state.participants };
      for (const participant of event.participants) {
        participants[participant.participantId] = participant.verifierId;
      }
      let next: GraphState = { ...state, participants, sessionId: event.sessionId };
      for (const participant of event.participants) {
        const node = next.nodes[participant.verifierId];
        if (node && (node.state === 'ghost' || node.state === 'live')) {
          next = patchNode(next, participant.verifierId, { state: 'pending' });
        }
      }
      return { ...next, phase: advancePhase(next.phase, 'verifying') };
    }

    case 'PARTICIPANT_RESPONDED': {
      const verifierId = state.participants[event.participantId];
      if (!verifierId || !state.nodes[verifierId]) {
        return state;
      }
      const patch: Partial<GraphNode> = { state: 'responded' };
      if (event.rating !== undefined) {
        patch.rating = event.rating;
      }
      return patchNode(state, verifierId, patch);
    }

    case 'PARTICIPANT_TIMED_OUT': {
      const verifierId = state.participants[event.participantId];
      if (!verifierId || !state.nodes[verifierId]) {
        return state;
      }
      return patchNode(state, verifierId, { state: 'timed_out' });
    }

    case 'SCORE_COMPUTED': {
      const previousScore =
        state.score && !scoresEqual(state.score, event.score) ? state.score : state.previousScore;
      let next: GraphState = { ...state, score: event.score, previousScore };
      const farmerId = findFarmerId(state);
      if (farmerId) {
        for (const verifierId of Object.values(state.participants)) {
          if (state.nodes[verifierId]?.state !== 'responded') {
            continue;
          }
          next = withEdge(next, {
            id: edgeId(verifierId, farmerId, 'evidence'),
            from: verifierId,
            to: farmerId,
            kind: 'evidence',
          });
        }
      }
      return { ...next, phase: advancePhase(next.phase, 'scored') };
    }

    case 'LOAN_CREATED': {
      let next = state;
      if (!next.nodes[event.loanId]) {
        next = withNode(next, {
          id: event.loanId,
          kind: 'loan',
          label: event.label ?? 'Loan',
          state: 'live',
          meta: { amount: event.amount, status: 'pending_disbursement', appliedAt: null },
        });
      }
      const farmerId = findFarmerId(state);
      if (farmerId) {
        next = withEdge(next, {
          id: edgeId(farmerId, event.loanId, 'financed'),
          from: farmerId,
          to: event.loanId,
          kind: 'financed',
        });
      }
      return { ...next, phase: advancePhase(next.phase, 'financed') };
    }

    case 'LOAN_DISBURSED': {
      const loan = state.nodes[event.loanId];
      if (!loan) {
        return state;
      }
      return patchNode(state, event.loanId, {
        meta: { ...loan.meta, status: 'disbursed' },
      });
    }

    case 'LOAN_RESOLVED': {
      const loan = state.nodes[event.loanId];
      if (!loan) {
        return state;
      }
      return patchNode(state, event.loanId, {
        meta: { ...loan.meta, status: event.outcome },
      });
    }

    case 'CREDIBILITY_UPDATED': {
      return patchNode(state, event.verifierId, { credibility: event.credibility });
    }

    case 'GRAPH_HYDRATED': {
      return event.state;
    }

    default: {
      const exhaustive: never = event;
      return exhaustive;
    }
  }
}
