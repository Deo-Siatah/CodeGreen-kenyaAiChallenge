import type { Decision, NodeKind, NodeState, Rating } from '@/domain/graph';

export interface KindStyle {
  colorVar: string;
  radius: number;
}

export const KIND_STYLE: Record<NodeKind, KindStyle> = {
  farmer: { colorVar: '--kind-farmer', radius: 26 },
  farm: { colorVar: '--kind-farm', radius: 18 },
  trust_source: { colorVar: '--kind-trust-source', radius: 15 },
  market_actor: { colorVar: '--kind-market-actor', radius: 15 },
  social_group: { colorVar: '--kind-social-group', radius: 15 },
  loan: { colorVar: '--kind-loan', radius: 20 },
};

export function kindColor(kind: NodeKind): string {
  return `hsl(var(${KIND_STYLE[kind].colorVar}))`;
}

const RATING_VAR: Record<Rating, string> = {
  1: '--rating-1',
  2: '--rating-2',
  3: '--rating-3',
  4: '--rating-4',
};

// Responded nodes shift from ember (weak) to gold-green (strong).
export function ratingColor(rating: Rating | undefined): string {
  const score = rating ?? 2;
  return `hsl(var(${RATING_VAR[score]}))`;
}

export function stateColor(state: NodeState, rating: Rating | undefined): string {
  switch (state) {
    case 'ghost':
      return 'hsl(var(--state-ghost))';
    case 'pending':
      return 'hsl(var(--state-pending))';
    case 'responded':
      return ratingColor(rating);
    case 'timed_out':
      return 'hsl(var(--state-timedout))';
    case 'live':
      return 'hsl(var(--node-glow))';
    default: {
      const exhaustive: never = state;
      return exhaustive;
    }
  }
}

export function decisionColor(decision: Decision): string {
  switch (decision) {
    case 'ELIGIBLE':
      return 'hsl(var(--decision-good))';
    case 'REVIEW_REQUIRED':
      return 'hsl(var(--decision-warn))';
    case 'DECLINE':
      return 'hsl(var(--decision-bad))';
    default: {
      const exhaustive: never = decision;
      return exhaustive;
    }
  }
}
