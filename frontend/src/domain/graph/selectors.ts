import type { GraphEdge, GraphNode, GraphState, NodeKind } from './types';

const KIND_ORDER: NodeKind[] = [
  'farmer',
  'farm',
  'trust_source',
  'market_actor',
  'social_group',
  'loan',
];

const VERIFIER_KINDS: NodeKind[] = ['trust_source', 'market_actor', 'social_group'];

function byId(a: { id: string }, b: { id: string }): number {
  if (a.id < b.id) return -1;
  if (a.id > b.id) return 1;
  return 0;
}

export function visibleNodes(state: GraphState): GraphNode[] {
  return Object.values(state.nodes).sort((a, b) => {
    const kindDiff = KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind);
    return kindDiff !== 0 ? kindDiff : byId(a, b);
  });
}

export function edgesOf(state: GraphState, nodeId: string): GraphEdge[] {
  return Object.values(state.edges)
    .filter((edge) => edge.from === nodeId || edge.to === nodeId)
    .sort(byId);
}

export function respondedCount(state: GraphState): number {
  return Object.values(state.nodes).filter((node) => node.state === 'responded').length;
}

export function allResponded(state: GraphState): boolean {
  const verifierIds = Object.values(state.participants);
  if (verifierIds.length === 0) {
    return false;
  }
  return verifierIds.every((verifierId) => state.nodes[verifierId]?.state === 'responded');
}

export function verifierIds(state: GraphState): string[] {
  return Object.values(state.nodes)
    .filter((node) => VERIFIER_KINDS.includes(node.kind))
    .map((node) => node.id)
    .sort();
}
