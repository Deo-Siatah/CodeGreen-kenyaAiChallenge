import type { VerificationResponsePayload } from '@/api/schemas';
import type { UssdChoice, UssdFlow, UssdStep } from './flows';

export interface UssdState {
  flow: UssdFlow;
  index: number;
  answers: Record<string, string>;
  complete: boolean;
}

export type UssdAction = { type: 'press'; key: string } | { type: 'back' };

export function startUssd(flow: UssdFlow): UssdState {
  return {
    flow,
    index: 0,
    answers: {},
    complete: flow.steps.length === 0,
  };
}

export function currentStep(state: UssdState): UssdStep | null {
  if (state.complete) {
    return null;
  }
  return state.flow.steps[state.index] ?? null;
}

export function chosenChoice(state: UssdState, key: string): UssdChoice | null {
  const step = currentStep(state);
  return step?.choices.find((item) => item.key === key) ?? null;
}

export function ussdReducer(state: UssdState, action: UssdAction): UssdState {
  if (action.type === 'back') {
    if (state.index === 0) {
      return state;
    }
    const previous = state.flow.steps[state.index - 1];
    if (!previous) {
      return state;
    }
    const answers = { ...state.answers };
    delete answers[previous.id];
    return { ...state, index: state.index - 1, answers, complete: false };
  }

  const step = currentStep(state);
  const picked = chosenChoice(state, action.key);
  if (!step || !picked) {
    return state;
  }

  const answers = { ...state.answers, [step.id]: picked.value };
  const ends = step.endWhen?.(answers) ?? false;
  const nextIndex = state.index + 1;
  return {
    ...state,
    answers,
    index: nextIndex,
    complete: ends || nextIndex >= state.flow.steps.length,
  };
}

function requireNumber(value: string | undefined, min: number, max: number): number {
  const number = Number(value);
  if (!Number.isFinite(number) || number < min || number > max) {
    throw new Error(`Unexpected USSD value: ${String(value)}`);
  }
  return number;
}

function nullableNumber(value: string | undefined): number | null {
  if (value === undefined || value === '') {
    return null;
  }
  return requireNumber(value, 0, Number.MAX_SAFE_INTEGER);
}

function nullableText(value: string | undefined): string | null {
  return value === undefined || value === '' ? null : value;
}

export function buildResponse(state: UssdState): VerificationResponsePayload | null {
  if (!state.complete) {
    return null;
  }

  const answers = state.answers;

  if (state.flow.kind === 'trust_source') {
    const knowsFarmer = answers.known === 'yes';
    return {
      participant_type: 'trust_source',
      rating: knowsFarmer ? requireNumber(answers.rating, 1, 4) : null,
      comments: null,
      personal_knowledge_flag: knowsFarmer,
    };
  }

  if (state.flow.kind === 'market_actor') {
    return {
      participant_type: 'market_actor',
      reliability_rating: requireNumber(answers.reliability, 1, 4),
      purchase_frequency: nullableText(answers.frequency),
      relationship_months: nullableNumber(answers.relationship),
      avg_volume_kg: nullableNumber(answers.volume),
    };
  }

  return {
    participant_type: 'social_group',
    consecutive_cycles: requireNumber(answers.cycles, 0, Number.MAX_SAFE_INTEGER),
    last_contribution_date: nullableText(answers.last_contribution),
    contribution_amount: nullableNumber(answers.amount),
  };
}
