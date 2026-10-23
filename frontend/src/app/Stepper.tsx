import { useI18n } from '@/i18n';
import type { TranslationKey } from '@/i18n';
import { useCaseStore } from './caseStore';
import { useGraphStore } from '@/features/graph/store';

const STEP_LABEL_KEYS: TranslationKey[] = [
  'case.steps.farmer',
  'case.steps.farm',
  'case.steps.network',
  'case.steps.verify',
  'case.steps.score',
  'case.steps.loan',
];

export function Stepper() {
  const { t } = useI18n();
  const step = useCaseStore((state) => state.step);
  const setStep = useCaseStore((state) => state.setStep);
  const nodes = useGraphStore((state) => state.nodes);
  const score = useGraphStore((state) => state.score);

  const kinds = new Set(Object.values(nodes).map((node) => node.kind));
  const hasFarmer = kinds.has('farmer');
  const hasFarm = kinds.has('farm');
  const hasVerifier = kinds.has('trust_source') || kinds.has('market_actor') || kinds.has('social_group');
  const hasScore = score !== null;

  const locks: boolean[] = [
    false,
    !hasFarmer,
    !hasFarm,
    !hasVerifier,
    !hasVerifier,
    !hasScore,
  ];

  return (
    <nav aria-label={t('case.steps.aria')} className="case-stepper">
      <ol>
        {STEP_LABEL_KEYS.map((key, index) => {
          const number = index + 1;
          const locked = locks[index] ?? true;
          return (
            <li key={key}>
              <button
                type="button"
                disabled={locked}
                aria-current={step === number ? 'step' : undefined}
                onClick={() => setStep(number)}
              >
                {`${number} ${t(key)}`}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
