import { z } from 'zod';
import type { components } from './generated/schema';

type ApiSchemas = components['schemas'];

const unknownRecord = z.record(z.string(), z.unknown());

// Farmer schemas - strict validation for requests
export const FarmerRouteCreate = z.object({
  full_name: z.string(),
  national_id: z.string(),
  phone: z.string(),
  gender: z.string(),
  date_of_birth: z.string().nullable(),
  location: z.string(),
  village: z.string().nullable(),
  sub_county: z.string().nullable(),
  county: z.string().nullable(),
  farming_type: z.string().nullable(),
  years_farming: z.number().nullable(),
}).strict() satisfies z.ZodType<ApiSchemas['FarmerRouteCreate']>;

export const FarmRouteCreate = z.object({
  acreage: z.number(),
  production_type: z.string().nullable(),
  latitude: z.number(),
  longitude: z.number(),
}).strict();

export const LinkRequest = z.object({
  related_id: z.string(),
}).strict() satisfies z.ZodType<ApiSchemas['LinkRequest']>;

// GET /api/farmers/{id} and POST /api/farmers return every table column.
export const FarmerDetailResponse = z.object({
  id: z.string(),
  full_name: z.string(),
  national_id: z.string(),
  phone: z.string(),
  gender: z.string(),
  date_of_birth: z.string().nullable(),
  location: z.string(),
  village: z.string().nullable(),
  sub_county: z.string().nullable(),
  county: z.string().nullable(),
  farming_type: z.string().nullable(),
  years_farming: z.number().nullable(),
  created_at: z.string(),
});

// POST /api/farmers/{id}/farm returns the farm row directly (untyped dict).
export const FarmResponse = z.object({
  id: z.string(),
  farmer_id: z.string(),
  acreage: z.number().nullable(),
  production_type: z.string().nullable(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
});

// GET /api/farmers returns only the summary projection.
export const FarmerResponse = z.object({
  id: z.string(),
  full_name: z.string(),
  county: z.string().nullable(),
  created_at: z.string(),
  current_score: z.object({
    final_score: z.number().nullable(),
    decision: z.string().nullable(),
    recommended_amount: z.number().nullable(),
  }).nullable(),
}) satisfies z.ZodType<ApiSchemas['FarmerResponse']>;

// Trust schemas - strict validation for requests
export const TrustSourceCreate = z.object({
  name: z.string(),
  category: z.string(),
  phone: z.string().nullable(),
  national_id: z.string().nullable(),
  location: z.string(),
}).strict() satisfies z.ZodType<ApiSchemas['TrustSourceCreate']>;

export const MarketActorCreate = z.object({
  name: z.string(),
  actor_type: z.string(),
  phone: z.string().nullable(),
  location: z.string(),
}).strict() satisfies z.ZodType<ApiSchemas['MarketActorCreate']>;

export const SocialGroupCreate = z.object({
  name: z.string(),
  group_type: z.string(),
  location: z.string(),
  formation_year: z.number().nullable(),
}).strict() satisfies z.ZodType<ApiSchemas['SocialGroupCreate']>;

// Trust entity responses. The backend returns the SQLAlchemy columns directly,
// so these intentionally allow extra fields (e.g. updated_at, institution_id).
export const TrustSourceEntity = z.object({
  id: z.string(),
  full_name: z.string(),
  category: z.string(),
  phone: z.string().nullable(),
  national_id: z.string().nullable(),
  location: z.string().nullable(),
  created_at: z.string(),
});

export const MarketActorEntity = z.object({
  id: z.string(),
  name: z.string(),
  actor_type: z.string().nullable(),
  phone: z.string().nullable(),
  location: z.string().nullable(),
  created_at: z.string(),
});

export const SocialGroupEntity = z.object({
  id: z.string(),
  name: z.string(),
  group_type: z.string().nullable(),
  location: z.string().nullable(),
  formation_year: z.number().nullable(),
  created_at: z.string(),
});

export const EntityLinkResponse = z.object({
  farmer_id: z.string(),
  trust_source_id: z.string().nullable().optional(),
  market_actor_id: z.string().nullable().optional(),
  social_group_id: z.string().nullable().optional(),
  relationship_type: z.string().nullable().optional(),
  years_known: z.number().nullable().optional(),
  created_at: z.string(),
});

// Verification answer schemas - strict validation for requests
export const TrustSourceResponse = z.object({
  participant_type: z.literal('trust_source'),
  rating: z.number().min(1).max(4).nullable(),
  comments: z.string().nullable(),
  personal_knowledge_flag: z.boolean(),
}).strict() satisfies z.ZodType<ApiSchemas['TrustSourceResponse']>;

export const MarketActorResponse = z.object({
  participant_type: z.literal('market_actor'),
  reliability_rating: z.number().min(1).max(4),
  purchase_frequency: z.string().nullable(),
  relationship_months: z.number().nullable(),
  avg_volume_kg: z.number().nullable(),
}).strict() satisfies z.ZodType<ApiSchemas['MarketActorResponse']>;

export const SocialGroupResponse = z.object({
  participant_type: z.literal('social_group'),
  consecutive_cycles: z.number().min(0),
  last_contribution_date: z.string().nullable(),
  contribution_amount: z.number().nullable(),
}).strict() satisfies z.ZodType<ApiSchemas['SocialGroupResponse']>;

export const VerificationResponsePayload = z.discriminatedUnion('participant_type', [
  TrustSourceResponse,
  MarketActorResponse,
  SocialGroupResponse,
]);

export const VerificationStartRequest = z.object({
  farmer_id: z.string(),
}).strict() satisfies z.ZodType<ApiSchemas['VerificationStartRequest']>;

export const VerificationStartResponse = z.object({
  session_id: z.string(),
  farmer_id: z.string(),
  status: z.string(),
});

export const VerificationParticipantStatus = z.object({
  id: z.string(),
  session_id: z.string(),
  participant_type: z.enum(['trust_source', 'market_actor', 'social_group']),
  participant_id: z.string(),
  contacted_at: z.string().nullable(),
  responded_at: z.string().nullable(),
  response: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const VerificationStatusResponse = z.object({
  session_id: z.string(),
  status: z.string(),
  participants: z.array(VerificationParticipantStatus),
});

export const VerificationSubmitResponse = z.object({
  participant_status: z.string().nullable(),
  session_status: z.string(),
  score_result: unknownRecord.nullable(),
});

export const VerificationTimeoutResponse = VerificationSubmitResponse;

export const ScoreProfileResponse = z.object({
  id: z.string(),
  farmer_id: z.string(),
  version: z.number(),
  character_score: z.number(),
  capacity_score: z.number().nullable(),
  final_score: z.number(),
  decision: z.string().nullable(),
  recommended_amount: z.number().nullable(),
  computed_at: z.string(),
  is_current: z.boolean(),
});

export const VerificationResultResponse = z.object({
  session_id: z.string(),
  score_profile: unknownRecord,
}) satisfies z.ZodType<ApiSchemas['VerificationResultResponse']>;

export const ExplanationResponse = z.object({
  session_id: z.string(),
  explanation: z.string(),
}) satisfies z.ZodType<ApiSchemas['ExplanationResponse']>;

// Settlement schema - strict validation for requests
export const SettlementRequest = z.object({
  settlement_type: z.string(),
  estimated_value: z.number(),
  verification_status: z.string().default('pending'),
  counterparty_id: z.string().nullable(),
}).strict();

// Loan schemas - strict validation for requests
export const LoanCreate = z.object({
  farmer_id: z.string(),
  amount: z.number().gt(0),
  purpose: z.string().nullable(),
  duration_months: z.number().gt(0).nullable(),
  interest_rate: z.number().gte(0).nullable(),
}).strict() satisfies z.ZodType<ApiSchemas['LoanCreate']>;

export const LoanResponse = z.object({
  id: z.string(),
  farmer_id: z.string(),
  amount: z.number(),
  purpose: z.string().nullable(),
  duration_months: z.number().nullable(),
  interest_rate: z.number().nullable(),
  status: z.string(),
  applied_at: z.string(),
  approved_at: z.string().nullable(),
  disbursed_at: z.string().nullable(),
  due_date: z.string().nullable(),
  repaid_at: z.string().nullable(),
  defaulted_at: z.string().nullable(),
  score_profile_id: z.string().nullable(),
});

// Dashboard aggregates from GET /api/stats/overview.
export const CountyCount = z.object({
  county: z.string().nullable(),
  count: z.number(),
});

export const FarmerStats = z.object({
  total: z.number(),
  scored: z.number(),
  unscored: z.number(),
  counties: z.array(CountyCount),
});

export const ScoreBucket = z.object({
  label: z.string(),
  count: z.number(),
});

export const DecisionStats = z.object({
  eligible: z.number(),
  review_required: z.number(),
  decline: z.number(),
  unscored: z.number(),
});

export const ScoreStats = z.object({
  scored: z.number(),
  mean_final: z.number().nullable(),
  mean_character: z.number().nullable(),
  mean_capacity: z.number().nullable(),
  buckets: z.array(ScoreBucket),
  decisions: DecisionStats,
});

export const NetworkStats = z.object({
  trust_sources: z.number(),
  market_actors: z.number(),
  social_groups: z.number(),
  links: z.number(),
  sessions: z.number(),
  completed_sessions: z.number(),
  participants: z.number(),
  responded_participants: z.number(),
  response_rate: z.number().nullable(),
});

export const RecentLoan = z.object({
  id: z.string(),
  farmer_id: z.string(),
  amount: z.number(),
  status: z.string(),
  applied_at: z.string(),
});

export const LoanStats = z.object({
  total: z.number(),
  pending: z.number(),
  pending_disbursement: z.number(),
  disbursed: z.number(),
  repaid: z.number(),
  defaulted: z.number(),
  total_amount: z.number(),
  disbursed_amount: z.number(),
  repaid_amount: z.number(),
  defaulted_amount: z.number(),
  repayment_rate: z.number().nullable(),
  recent: z.array(RecentLoan),
});

export const ComponentStats = z.object({
  component_name: z.string(),
  mean_contribution: z.number(),
  sample_size: z.number(),
});

export const GenderScore = z.object({
  gender: z.string(),
  count: z.number(),
  mean_final: z.number().nullable(),
});

export const ScatterPoint = z.object({
  acreage: z.number(),
  final_score: z.number(),
});

export const FairnessStats = z.object({
  excluded_inputs: z.array(z.string()),
  character_axis_weight: z.number(),
  capacity_axis_weight: z.number(),
  capacity_coverage: z.number().nullable(),
  gender: z.array(GenderScore),
  acreage_vs_score: z.array(ScatterPoint),
  acreage_score_correlation: z.number().nullable(),
});

export const RecentCase = z.object({
  id: z.string(),
  full_name: z.string(),
  county: z.string().nullable(),
  final_score: z.number().nullable(),
  decision: z.string().nullable(),
  recommended_amount: z.number().nullable(),
  created_at: z.string(),
  loan_status: z.string().nullable(),
});

export const StatsOverviewResponse = z.object({
  generated_at: z.string(),
  farmers: FarmerStats,
  scores: ScoreStats,
  network: NetworkStats,
  loans: LoanStats,
  components: z.array(ComponentStats),
  fairness: FairnessStats,
  recent_cases: z.array(RecentCase),
}) satisfies z.ZodType<ApiSchemas['StatsOverviewResponse']>;

// List response schemas
export const FarmersListResponse = z.object({
  items: z.array(FarmerResponse),
  total: z.number(),
}) satisfies z.ZodType<ApiSchemas['FarmersListResponse']>;

export const NetworkResponse = z.object({
  farmer: unknownRecord,
  farms: z.array(z.object({
    id: z.string(),
    acreage: z.number().nullable(),
    latitude: z.number().nullable(),
    longitude: z.number().nullable(),
  })),
  trust_sources: z.array(z.object({
    id: z.string(),
    name: z.string(),
    category: z.string(),
    phone_masked: z.string().nullable(),
    credibility_score: z.number(),
  })),
  market_actors: z.array(z.object({
    id: z.string(),
    name: z.string(),
    actor_type: z.string().nullable(),
    phone_masked: z.string().nullable(),
    credibility_score: z.number(),
  })),
  social_groups: z.array(z.object({
    id: z.string(),
    name: z.string(),
    group_type: z.string().nullable(),
  })),
  latest_session: z.object({
    id: z.string(),
    status: z.string(),
    participants: z.array(z.object({
      id: z.string(),
      participant_type: z.string(),
      participant_id: z.string(),
      responded: z.string().nullable(),
    })),
  }).nullable(),
  current_score: z.object({
    id: z.string(),
    character_score: z.number().nullable(),
    capacity_score: z.number().nullable(),
    final_score: z.number().nullable(),
    decision: z.string().nullable(),
    recommended_amount: z.number().nullable(),
  }).nullable(),
  loans: z.array(z.object({
    id: z.string(),
    amount: z.number().nullable(),
    status: z.string(),
    applied_at: z.string().nullable(),
  })),
}) satisfies z.ZodType<ApiSchemas['NetworkResponse']>;

export const BreakdownResponse = z.object({
  profile: unknownRecord,
  axis_note: z.string(),
  components: z.array(z.object({
    axis: z.string(),
    component_name: z.string(),
    raw_value: z.string(),
    contribution: z.number().nullable(),
    weight: z.number().nullable(),
    pool_id: z.string().nullable(),
    trust_source_id: z.string().nullable(),
    market_actor_id: z.string().nullable(),
  })),
}) satisfies z.ZodType<ApiSchemas['BreakdownResponse']>;

// Export all schemas
export const schemas = {
  FarmerRouteCreate,
  FarmRouteCreate,
  LinkRequest,
  FarmerDetailResponse,
  FarmResponse,
  FarmerResponse,
  TrustSourceCreate,
  MarketActorCreate,
  SocialGroupCreate,
  TrustSourceEntity,
  MarketActorEntity,
  SocialGroupEntity,
  EntityLinkResponse,
  TrustSourceResponse,
  MarketActorResponse,
  SocialGroupResponse,
  VerificationResponsePayload,
  VerificationStartRequest,
  VerificationStartResponse,
  VerificationParticipantStatus,
  VerificationStatusResponse,
  VerificationSubmitResponse,
  VerificationTimeoutResponse,
  ScoreProfileResponse,
  VerificationResultResponse,
  ExplanationResponse,
  SettlementRequest,
  LoanCreate,
  LoanResponse,
  FarmersListResponse,
  NetworkResponse,
  BreakdownResponse,
  StatsOverviewResponse,
  CountyCount,
  FarmerStats,
  ScoreBucket,
  DecisionStats,
  ScoreStats,
  NetworkStats,
  RecentLoan,
  LoanStats,
  ComponentStats,
  GenderScore,
  ScatterPoint,
  FairnessStats,
  RecentCase,
};

// Inferred types so endpoint modules can import them with `import type`.
export type FarmerRouteCreate = z.infer<typeof FarmerRouteCreate>;
export type FarmerDetailResponse = z.infer<typeof FarmerDetailResponse>;
export type FarmRouteCreate = z.infer<typeof FarmRouteCreate>;
export type FarmResponse = z.infer<typeof FarmResponse>;
export type FarmerResponse = z.infer<typeof FarmerResponse>;
export type TrustSourceCreate = z.infer<typeof TrustSourceCreate>;
export type MarketActorCreate = z.infer<typeof MarketActorCreate>;
export type SocialGroupCreate = z.infer<typeof SocialGroupCreate>;
export type LinkRequest = z.infer<typeof LinkRequest>;
export type VerificationStartRequest = z.infer<typeof VerificationStartRequest>;
export type TrustSourceResponse = z.infer<typeof TrustSourceResponse>;
export type MarketActorResponse = z.infer<typeof MarketActorResponse>;
export type SocialGroupResponse = z.infer<typeof SocialGroupResponse>;
export type VerificationResponsePayload = z.infer<typeof VerificationResponsePayload>;
export type VerificationStatusResponse = z.infer<typeof VerificationStatusResponse>;
export type ScoreProfileResponse = z.infer<typeof ScoreProfileResponse>;
export type BreakdownResponse = z.infer<typeof BreakdownResponse>;
export type LoanCreate = z.infer<typeof LoanCreate>;
export type LoanResponse = z.infer<typeof LoanResponse>;
export type NetworkResponse = z.infer<typeof NetworkResponse>;
export type StatsOverviewResponse = z.infer<typeof StatsOverviewResponse>;
export type FarmerStats = z.infer<typeof FarmerStats>;
export type ScoreStats = z.infer<typeof ScoreStats>;
export type LoanStats = z.infer<typeof LoanStats>;
export type FairnessStats = z.infer<typeof FairnessStats>;
export type RecentCase = z.infer<typeof RecentCase>;
export type ScatterPoint = z.infer<typeof ScatterPoint>;
