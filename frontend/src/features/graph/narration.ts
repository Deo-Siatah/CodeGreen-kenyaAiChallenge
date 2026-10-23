import type { GraphEvent } from '@/domain/graph';
import { makeTranslator, type Translator } from '@/i18n/dictionary';

const english = makeTranslator('en');

export function describeEvent(event: GraphEvent, t: Translator = english): string {
  switch (event.type) {
    case 'FARMER_CREATED':
      return t('narration.farmerCreated', { name: event.label });
    case 'FARM_CREATED':
      return t('narration.farmCreated');
    case 'VERIFIER_ADDED':
      return t('narration.verifierAdded', { name: event.label });
    case 'VERIFIER_LINKED':
      return t('narration.verifierLinked');
    case 'SESSION_STARTED':
      return t('narration.sessionStarted', { count: event.participants.length });
    case 'PARTICIPANT_RESPONDED':
      return t('narration.participantResponded');
    case 'PARTICIPANT_TIMED_OUT':
      return t('narration.participantTimedOut');
    case 'SCORE_COMPUTED':
      return t('narration.scoreComputed', { score: event.score.final });
    case 'LOAN_CREATED':
      return t('narration.loanCreated', { amount: event.amount });
    case 'LOAN_DISBURSED':
      return t('narration.loanDisbursed');
    case 'LOAN_RESOLVED':
      return t('narration.loanResolved', { outcome: event.outcome });
    case 'CREDIBILITY_UPDATED':
      return t('narration.credibilityUpdated', { credibility: event.credibility });
    case 'GRAPH_HYDRATED':
      return t('narration.graphHydrated');
    default: {
      const exhaustive: never = event;
      return exhaustive;
    }
  }
}
