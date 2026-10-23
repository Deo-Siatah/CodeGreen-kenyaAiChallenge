import type { VerifierKind } from '@/domain/graph';
import { makeTranslator, type Language, type Translator } from '@/i18n/dictionary';

export interface UssdChoice {
  key: string;
  label: string;
  value: string;
}

export interface UssdStep {
  id: string;
  prompt: string;
  choices: UssdChoice[];
  endWhen?: (answers: Readonly<Record<string, string>>) => boolean;
}

export interface UssdFlow {
  kind: VerifierKind;
  name: string;
  steps: UssdStep[];
}

function firstNameOf(fullName: string, fallback: string): string {
  const [first] = fullName.trim().split(/\s+/);
  return first && first.length > 0 ? first : fallback;
}

function choice(key: number | string, label: string, value: string): UssdChoice {
  return { key: String(key), label, value };
}

function ratingStep(id: string, prompt: string, t: Translator): UssdStep {
  return {
    id,
    prompt,
    choices: [
      choice(1, t('ussd.poor'), '1'),
      choice(2, t('ussd.fair'), '2'),
      choice(3, t('ussd.good'), '3'),
      choice(4, t('ussd.excellent'), '4'),
    ],
  };
}

function monthsAgo(now: Date, months: number): string {
  const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - months, 1));
  return date.toISOString().slice(0, 10);
}

function trustSourceFlow(name: string, t: Translator): UssdFlow {
  return {
    kind: 'trust_source',
    name,
    steps: [
      {
        id: 'known',
        prompt: t('ussd.known', { name }),
        choices: [choice(1, t('ussd.yes'), 'yes'), choice(2, t('ussd.no'), 'no')],
        endWhen: (answers) => answers.known === 'no',
      },
      ratingStep('rating', t('ussd.rate', { name }), t),
      {
        id: 'comments',
        prompt: t('ussd.comments', { name }),
        choices: [choice(1, t('ussd.skipAll'), 'skip')],
      },
    ],
  };
}

function marketActorFlow(name: string, t: Translator): UssdFlow {
  return {
    kind: 'market_actor',
    name,
    steps: [
      ratingStep('reliability', t('ussd.reliability', { name }), t),
      {
        id: 'frequency',
        prompt: t('ussd.frequency', { name }),
        choices: [
          choice(1, t('ussd.weekly'), 'weekly'),
          choice(2, t('ussd.monthly'), 'monthly'),
          choice(3, t('ussd.seasonal'), 'seasonal'),
        ],
      },
      {
        id: 'relationship',
        prompt: t('ussd.relationship', { name }),
        choices: [
          choice(1, t('ussd.underSixMonths'), '3'),
          choice(2, t('ussd.sixToTwelve'), '9'),
          choice(3, t('ussd.oneToTwoYears'), '18'),
          choice(4, t('ussd.overTwoYears'), '30'),
        ],
      },
      {
        id: 'volume',
        prompt: t('ussd.volume'),
        choices: [
          choice(1, t('ussd.skip'), ''),
          choice(2, t('ussd.under100'), '50'),
          choice(3, t('ussd.100to500'), '300'),
          choice(4, t('ussd.over500'), '800'),
        ],
      },
    ],
  };
}

function socialGroupFlow(name: string, now: Date, t: Translator): UssdFlow {
  return {
    kind: 'social_group',
    name,
    steps: [
      {
        id: 'cycles',
        prompt: t('ussd.cycles', { name }),
        choices: [
          choice(1, t('ussd.noneYet'), '0'),
          choice(2, t('ussd.oneToTwo'), '2'),
          choice(3, t('ussd.threeToFive'), '4'),
          choice(4, t('ussd.sixOrMore'), '6'),
        ],
      },
      {
        id: 'last_contribution',
        prompt: t('ussd.lastContribution'),
        choices: [
          choice(1, t('ussd.thisMonth'), monthsAgo(now, 0)),
          choice(2, t('ussd.oneToThreeMonths'), monthsAgo(now, 2)),
          choice(3, t('ussd.longerAgo'), monthsAgo(now, 6)),
          choice(4, t('ussd.never'), ''),
        ],
      },
      {
        id: 'amount',
        prompt: t('ussd.amount'),
        choices: [
          choice(1, t('ussd.skip'), ''),
          choice(2, t('ussd.under500'), '250'),
          choice(3, t('ussd.500to2000'), '1000'),
          choice(4, t('ussd.over2000'), '3000'),
        ],
      },
    ],
  };
}

export function buildFlow(
  kind: VerifierKind,
  fullName: string,
  now: Date = new Date(),
  language: Language = 'en',
): UssdFlow {
  const t = makeTranslator(language);
  const name = firstNameOf(fullName, t('ussd.theFarmer'));
  switch (kind) {
    case 'trust_source':
      return trustSourceFlow(name, t);
    case 'market_actor':
      return marketActorFlow(name, t);
    case 'social_group':
      return socialGroupFlow(name, now, t);
  }
}
