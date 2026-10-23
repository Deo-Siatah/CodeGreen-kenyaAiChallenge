import { titleCase } from '@/lib/format';
import type { TranslationKey, Translator } from './dictionary';

const decisionKeys: Record<string, TranslationKey> = {
  eligible: 'decision.eligible',
  review: 'decision.review',
  review_required: 'decision.review',
  decline: 'decision.decline',
  pending: 'decision.pending',
};

const loanKeys: Record<string, TranslationKey> = {
  pending: 'loan.pending',
  pending_disbursement: 'loan.pendingDisbursement',
  disbursed: 'loan.disbursed',
  repaid: 'loan.repaid',
  defaulted: 'loan.defaulted',
};

const componentKeys: Record<string, TranslationKey> = {
  community_testimony: 'component.communityTestimony',
  testimony: 'component.testimony',
  testimony_pool: 'component.testimonyPool',
  buyer_relationship: 'component.buyerRelationship',
  buyer_relationship_pool: 'component.buyerRelationshipPool',
  discipline_proxy: 'component.disciplineProxy',
  discipline_proxy_pool: 'component.disciplineProxyPool',
  cultivation_continuity: 'component.cultivationContinuity',
  in_kind_settlement: 'component.inKindSettlement',
  in_kind_settlement_pool: 'component.inKindSettlementPool',
  testimony_agreement: 'component.testimonyAgreement',
};

const excludedKeys: Record<string, TranslationKey> = {
  gender: 'excluded.gender',
  ethnicity: 'excluded.ethnicity',
  religion: 'excluded.religion',
  disability: 'excluded.disability',
  age: 'excluded.age',
  raw_acreage: 'excluded.rawAcreage',
};

const verifierKeys: Record<string, TranslationKey> = {
  trust_source: 'verifier.community',
  community: 'verifier.community',
  market_actor: 'verifier.buyer',
  buyer: 'verifier.buyer',
  social_group: 'verifier.savingsGroup',
  savings_group: 'verifier.savingsGroup',
};

const phaseKeys: Record<string, TranslationKey> = {
  empty: 'phase.empty',
  farmer: 'phase.farmer',
  farm: 'phase.farm',
  network: 'phase.network',
  verifying: 'phase.verifying',
  scored: 'phase.scored',
  financed: 'phase.financed',
};

const sessionStatusKeys: Record<string, TranslationKey> = {
  pending: 'case.verify.status.pending',
  in_progress: 'case.verify.status.inProgress',
  completed: 'case.verify.status.completed',
  insufficient_data: 'case.verify.status.insufficient',
  unknown: 'case.verify.status.unknown',
};

const presetKeys: Record<string, TranslationKey> = {
  'administrative official': 'preset.community.administrative',
  'family member': 'preset.community.family',
  neighbour: 'preset.community.neighbour',
  friend: 'preset.community.friend',
  buyer: 'preset.buyer.buyer',
  aggregator: 'preset.buyer.aggregator',
  agrovet: 'preset.buyer.agrovet',
  processor: 'preset.buyer.processor',
  cooperative: 'preset.buyer.cooperative',
  sacco: 'preset.group.sacco',
  chama: 'preset.group.chama',
  'table banking': 'preset.group.tableBanking',
  'self help group': 'preset.group.selfHelp',
  crop: 'preset.production.crop',
  livestock: 'preset.production.livestock',
  mixed: 'preset.production.mixed',
  female: 'preset.gender.female',
  male: 'preset.gender.male',
  other: 'preset.gender.other',
};

function normalized(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, '_');
}

function lookup(
  values: Record<string, TranslationKey>,
  value: string,
  t: Translator,
): string | null {
  const key = values[normalized(value)];
  return key ? t(key) : null;
}

export function decisionLabel(value: string | null | undefined, t: Translator): string {
  if (!value) {
    return t('common.unscored');
  }
  return lookup(decisionKeys, value, t) ?? titleCase(value);
}

export function loanStatusLabel(value: string | null | undefined, t: Translator): string {
  if (!value) {
    return t('common.noLoan');
  }
  return lookup(loanKeys, value, t) ?? titleCase(value);
}

export function componentLabel(value: string, t: Translator): string {
  return lookup(componentKeys, value, t) ?? titleCase(value.replace(/_/g, ' '));
}

export function excludedInputLabel(value: string, t: Translator): string {
  return lookup(excludedKeys, value, t) ?? titleCase(value.replace(/_/g, ' '));
}

export function verifierKindLabel(value: string, t: Translator): string {
  return lookup(verifierKeys, value, t) ?? titleCase(value.replace(/_/g, ' '));
}

export function presetLabel(value: string, t: Translator): string {
  return lookup(presetKeys, value, t) ?? value;
}

export function sessionStatusLabel(value: string, t: Translator): string {
  return lookup(sessionStatusKeys, value, t) ?? t('case.verify.status.unknown');
}

export function phaseLabel(value: string, t: Translator): string {
  return lookup(phaseKeys, value, t) ?? value;
}

export function genderLabel(value: string | null | undefined, t: Translator): string {
  if (!value) {
    return t('gender.unknown');
  }
  return lookup(presetKeys, value, t) ?? titleCase(value);
}
