export type NodeKind =
  | 'farmer'
  | 'farm'
  | 'trust_source'
  | 'market_actor'
  | 'social_group'
  | 'loan';

export type VerifierKind = 'trust_source' | 'market_actor' | 'social_group';

export type NodeState = 'ghost' | 'live' | 'pending' | 'responded' | 'timed_out';

export type EdgeKind =
  | 'owns'
  | 'vouches'
  | 'buys_from'
  | 'member_of'
  | 'evidence'
  | 'financed';

export type Phase =
  | 'empty'
  | 'farmer'
  | 'farm'
  | 'network'
  | 'verifying'
  | 'scored'
  | 'financed';

export type Decision = 'ELIGIBLE' | 'REVIEW_REQUIRED' | 'DECLINE';

export type Rating = 1 | 2 | 3 | 4;

export type MetaValue = string | number | null;

export interface GraphNode {
  id: string;
  kind: NodeKind;
  label: string;
  state: NodeState;
  rating?: Rating;
  credibility?: number;
  meta: Record<string, MetaValue>;
}

export interface GraphEdge {
  id: string;
  from: string;
  to: string;
  kind: EdgeKind;
  weight?: number;
}

export interface Score {
  final: number;
  character: number;
  capacity: number | null;
  decision: Decision;
  recommendedAmount: number | null;
}

export interface ParticipantRef {
  participantId: string;
  verifierId: string;
}

export interface GraphState {
  nodes: Record<string, GraphNode>;
  edges: Record<string, GraphEdge>;
  phase: Phase;
  participants: Record<string, string>;
  sessionId: string | null;
  score: Score | null;
  previousScore: Score | null;
}

export type GraphEvent =
  | { type: 'FARMER_CREATED'; farmerId: string; label: string }
  | {
      type: 'FARM_CREATED';
      farmId: string;
      farmerId: string;
      label?: string;
      acreage?: number | null;
      latitude?: number | null;
      longitude?: number | null;
    }
  | { type: 'VERIFIER_ADDED'; verifierId: string; kind: VerifierKind; label: string }
  | { type: 'VERIFIER_LINKED'; farmerId: string; verifierId: string; kind: VerifierKind }
  | { type: 'SESSION_STARTED'; sessionId: string; participants: ParticipantRef[] }
  | { type: 'PARTICIPANT_RESPONDED'; participantId: string; rating?: Rating }
  | { type: 'PARTICIPANT_TIMED_OUT'; participantId: string }
  | { type: 'SCORE_COMPUTED'; score: Score }
  | { type: 'LOAN_CREATED'; loanId: string; amount: number; label?: string }
  | { type: 'LOAN_DISBURSED'; loanId: string }
  | { type: 'LOAN_RESOLVED'; loanId: string; outcome: 'repaid' | 'defaulted' }
  | { type: 'CREDIBILITY_UPDATED'; verifierId: string; credibility: number }
  | { type: 'GRAPH_HYDRATED'; state: GraphState };
