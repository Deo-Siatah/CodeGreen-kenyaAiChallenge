import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ApiError } from '@/api/errors';
import { getFarmerNetwork } from '@/api/endpoints/farmers';
import { clearRequestLog } from '@/api/requestLog';
import { eventsFromNetwork } from '@/domain/graph';
import { GraphCanvas } from '@/features/graph/GraphCanvas';
import { useGraphStore } from '@/features/graph/store';
import { useI18n } from '@/i18n';
import { LanguageToggle } from '@/i18n/LanguageToggle';
import { ThemeToggle } from '@/theme';
import { EvidenceLedger } from './EvidenceLedger';
import { Stepper } from './Stepper';
import { useCaseStore } from './caseStore';
import { StepFarmer } from './steps/StepFarmer';
import { StepFarm } from './steps/StepFarm';
import { StepLoan } from './steps/StepLoan';
import { StepNetwork } from './steps/StepNetwork';
import { StepScore } from './steps/StepScore';
import { StepVerify } from './steps/StepVerify';
import './case.css';

function deriveStep(): number {
  const kinds = new Set(Object.values(useGraphStore.getState().nodes).map((node) => node.kind));
  if (!kinds.has('farmer')) {
    return 1;
  }
  if (!kinds.has('farm')) {
    return 2;
  }
  if (kinds.has('loan')) {
    return 6;
  }
  if (kinds.has('trust_source') || kinds.has('market_actor') || kinds.has('social_group')) {
    return 4;
  }
  return 3;
}

function ActiveStep() {
  const step = useCaseStore((state) => state.step);

  switch (step) {
    case 1:
      return <StepFarmer />;
    case 2:
      return <StepFarm />;
    case 3:
      return <StepNetwork />;
    case 4:
      return <StepVerify />;
    case 5:
      return <StepScore />;
    case 6:
      return <StepLoan />;
    default:
      return <StepFarmer />;
  }
}

export function CaseLayout() {
  const { t } = useI18n();
  const { caseId } = useParams<{ caseId: string }>();
  const status = useCaseStore((state) => state.status);
  const error = useCaseStore((state) => state.error);

  useEffect(() => {
    useGraphStore.getState().reset();
    clearRequestLog();
    useCaseStore.getState().reset();

    if (!caseId || caseId === 'new') {
      useCaseStore.getState().beginCase('new');
      useCaseStore.getState().setStatus('idle');
      return;
    }

    const id = caseId;
    useCaseStore.getState().beginCase(id);
    const controller = new AbortController();

    void (async () => {
      try {
        const network = await getFarmerNetwork(id, controller.signal);
        useCaseStore.getState().setStatus('ready');
        await useGraphStore.getState().dispatch(eventsFromNetwork(network));
        useCaseStore.getState().setStep(deriveStep());
      } catch (err) {
        if (err instanceof ApiError && err.kind === 'cancelled') {
          return;
        }
        if (err instanceof ApiError && err.kind === 'not_found') {
          useCaseStore.getState().setStatus('not_found', err.message);
          return;
        }
        useCaseStore
          .getState()
          .setStatus('error', err instanceof ApiError ? err.message : t('case.loadError'));
      }
    })();

    return () => controller.abort();
  }, [caseId, t]);

  return (
    <main className="case-layout">
      <section className="case-stage" aria-label={t('case.stageAria')}>
        <GraphCanvas />
      </section>
      <aside className="case-panel">
        <div className="case-panel__toolbar">
          <LanguageToggle />
          <ThemeToggle />
        </div>
        <Stepper />
        {status === 'hydrating' && (
          <p className="case-status">{t('case.hydrating')}</p>
        )}
        {status === 'not_found' && (
          <p className="case-status" role="alert">
            {error ?? t('case.notFound')}
          </p>
        )}
        {status === 'error' && (
          <p className="case-status" role="alert">
            {error}
          </p>
        )}
        {(status === 'idle' || status === 'ready') && <ActiveStep />}
        <EvidenceLedger />
      </aside>
    </main>
  );
}
