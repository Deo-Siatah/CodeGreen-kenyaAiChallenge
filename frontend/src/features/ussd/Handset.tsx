import { useState } from 'react';
import type { VerificationResponsePayload } from '@/api/schemas';
import { Button } from '@/components/ui/button';
import { useI18n } from '@/i18n';
import type { UssdFlow } from './flows';
import { buildResponse, currentStep, startUssd, ussdReducer } from './machine';

interface HandsetProps {
  flow: UssdFlow;
  pending?: boolean;
  error?: string | null;
  onSubmit: (response: VerificationResponsePayload) => void;
  onCancel: () => void;
}

export function Handset({ flow, pending = false, error = null, onSubmit, onCancel }: HandsetProps) {
  const { t } = useI18n();
  const [state, setState] = useState(() => startUssd(flow));
  const step = currentStep(state);

  return (
    <section
      className="ussd-handset"
      role="group"
      aria-label={t('ussd.aria', { name: flow.name })}
    >
      <header className="ussd-handset__header">
        <span className="ussd-handset__carrier">{t('ussd.carrier')}</span>
        <span>{flow.name}</span>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={pending}>
          {t('common.cancel')}
        </Button>
      </header>

      <div className="ussd-handset__screen">
        {state.complete ? (
          <p className="ussd-handset__prompt" data-testid="ussd-prompt">
            {t('ussd.ready')}
          </p>
        ) : (
          <p className="ussd-handset__prompt" data-testid="ussd-prompt">
            {step?.prompt}
          </p>
        )}
      </div>

      {state.complete ? (
        <div className="ussd-handset__actions">
          <Button
            type="button"
            onClick={() => {
              const response = buildResponse(state);
              if (response) {
                onSubmit(response);
              }
            }}
            disabled={pending}
          >
            {pending ? t('ussd.sending') : t('ussd.send')}
          </Button>
        </div>
      ) : (
        <>
          <div className="ussd-handset__choices">
            {step?.choices.map((choice) => (
              <Button
                key={choice.key}
                type="button"
                variant="outline"
                className="ussd-handset__choice"
                aria-label={t('ussd.choiceAria', {
                  key: choice.key,
                  label: choice.label,
                })}
                onClick={() => setState((current) => ussdReducer(current, { type: 'press', key: choice.key }))}
                disabled={pending}
              >
                <span className="ussd-handset__key">{choice.key}</span>
                {choice.label}
              </Button>
            ))}
          </div>
          <div className="ussd-handset__actions">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setState((current) => ussdReducer(current, { type: 'back' }))}
              disabled={pending || state.index === 0}
            >
              {t('ussd.back')}
            </Button>
          </div>
        </>
      )}

      {error ? (
        <p className="ussd-handset__error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
