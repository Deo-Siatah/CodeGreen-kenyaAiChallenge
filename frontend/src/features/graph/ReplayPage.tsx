import { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import type { BreakdownResponse, ScoreProfileResponse } from '@/api/schemas';
import { schemas } from '@/api/schemas';
import { Breakdown } from '@/app/steps/Breakdown';
import { ScoreCard } from '@/app/steps/ScoreCard';
import { translate, useI18n } from '@/i18n';
import { LanguageToggle } from '@/i18n/LanguageToggle';
import { decisionLabel } from '@/i18n/labels';
import { ThemeToggle } from '@/theme';
import { formatMoney, formatScore } from '@/lib/format';
import { defaultReplay, replayEvents } from '@/replay';
import { GraphCanvas } from './GraphCanvas';
import { useGraphStore } from './store';
import { useReducedMotionPreference } from './useReducedMotion';
import '@/app/case.css';
import './graph.css';

const replayLog = replayEvents(defaultReplay);

function formatRecordedDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(value));
}

function recordedProfile(breakdown: BreakdownResponse | undefined): ScoreProfileResponse | null {
  if (!breakdown) {
    return null;
  }
  const parsed = schemas.ScoreProfileResponse.safeParse(breakdown.profile);
  return parsed.success ? parsed.data : null;
}

export function ReplayPage() {
  const { t, locale } = useI18n();
  const playing = useGraphStore((state) => state.playing);
  const score = useGraphStore((state) => state.score);
  const dispatch = useGraphStore((state) => state.dispatch);
  const reset = useGraphStore((state) => state.reset);
  const cancel = useGraphStore((state) => state.cancel);
  const nodeCount = useGraphStore((state) => Object.keys(state.nodes).length);
  const replayedCount = useGraphStore((state) => state.log.length);
  const reducedMotion = useReducedMotionPreference();
  const breakdown = defaultReplay.breakdown;
  const profile = useMemo(() => recordedProfile(breakdown), [breakdown]);

  useEffect(() => {
    reset();
  }, [reset]);

  function start(instant: boolean) {
    reset();
    void dispatch(replayLog, { instant: instant || reducedMotion });
  }

  const bodyKey =
    score && score.capacity === null
      ? 'replay.translation.bodyCharacterOnly'
      : 'replay.translation.body';
  const recordedName = defaultReplay.network.farmer.full_name;
  const name = typeof recordedName === 'string' ? recordedName : defaultReplay.label;
  const scoreVars = score
    ? {
        name,
        character: formatScore(score.character),
        capacity: formatScore(score.capacity),
        final: formatScore(score.final),
        amount: formatMoney(score.recommendedAmount),
      }
    : null;
  const enDecision = score
    ? decisionLabel(score.decision, (key, vars) => translate('en', key, vars))
    : '';
  const swDecision = score
    ? decisionLabel(score.decision, (key, vars) => translate('sw', key, vars))
    : '';
  const formula = score
    ? score.capacity === null
      ? t('replay.calculation.formulaCharacterOnly', {
          character: formatScore(score.character),
          final: formatScore(score.final),
        })
      : t('replay.calculation.formula', {
          character: formatScore(score.character),
          capacity: formatScore(score.capacity),
          final: formatScore(score.final),
        })
    : null;

  return (
    <div className="replay">
      <header className="replay__header">
        <div className="replay__identity">
          <p className="replay__eyebrow">{t('replay.eyebrow')}</p>
          <h1>{t('replay.title')}</h1>
          <p className="replay__label" data-testid="replay-label">
            {defaultReplay.label}
          </p>
          <p className="replay__meta">
            {t('replay.recorded', {
              date: formatRecordedDate(defaultReplay.recordedAt, locale),
            })}
          </p>
          <p className="replay__source">
            {t('replay.source', { source: defaultReplay.source })}
          </p>
          <Link className="replay__back" to="/">
            {t('replay.backToPortfolio')}
          </Link>
        </div>

        <div className="replay__controls">
          <button type="button" onClick={() => start(false)} disabled={playing}>
            {t('replay.play')}
          </button>
          <button type="button" onClick={() => start(true)}>
            {t('replay.fastForward')}
          </button>
          <button type="button" onClick={() => cancel()} disabled={!playing}>
            {t('replay.cancel')}
          </button>
          <button type="button" onClick={() => reset()}>
            {t('replay.reset')}
          </button>
          <LanguageToggle />
          <ThemeToggle />
        </div>

        <div className="replay__counts" aria-live="polite">
          <span>{t('replay.events', { count: replayedCount })}</span>
          <span>{t('replay.nodes', { count: nodeCount })}</span>
          <span>{t('replay.ready', { count: replayLog.length })}</span>
        </div>
      </header>

      <div className="replay__stage" aria-label={t('replay.stageAria')}>
        <GraphCanvas />
      </div>

      <section className="replay__result" aria-labelledby="replay-result-title">
        <header className="replay__result-header">
          <p className="replay__eyebrow">{t('replay.eyebrow')}</p>
          <h2 id="replay-result-title">{t('replay.result.title')}</h2>
        </header>

        {!score ? (
          <p className="replay__pending">{t('replay.result.pending')}</p>
        ) : (
          <>
            <div data-testid="replay-score">
              {profile ? (
                <ScoreCard profile={profile} />
              ) : (
                <section className="score-card" aria-label={t('score.final')}>
                  <div className="score-card__headline">
                    <span className="score-card__label">{t('score.final')}</span>
                    <strong className="score-card__final">{formatScore(score.final)}</strong>
                    <span
                      className="score-card__decision"
                      data-decision={score.decision}
                    >
                      {decisionLabel(score.decision, t)}
                    </span>
                  </div>
                </section>
              )}
            </div>

            <section className="replay__calculation" data-testid="replay-calculation">
              <h3>{t('replay.calculation.title')}</h3>
              <p className="replay__formula">{formula}</p>
              <p className="replay__weights">{t('replay.calculation.weights')}</p>
            </section>

            {breakdown ? (
              <Breakdown components={breakdown.components} axisNote={breakdown.axis_note} />
            ) : null}

            <section className="replay__translation" data-testid="replay-translation">
              <header>
                <h3>{t('replay.translation.title')}</h3>
                <p>{t('replay.translation.description')}</p>
              </header>
              <div className="replay__translation-grid">
                <article className="replay__translation-card" data-testid="replay-translation-en">
                  <h4>{translate('en', 'replay.translation.english')}</h4>
                  <p>
                    {scoreVars
                      ? translate('en', bodyKey, { ...scoreVars, decision: enDecision })
                      : null}
                  </p>
                </article>
                <article
                  className="replay__translation-card"
                  lang="sw"
                  data-testid="replay-translation-sw"
                >
                  <h4>{translate('sw', 'replay.translation.swahili')}</h4>
                  <p>
                    {scoreVars
                      ? translate('sw', bodyKey, { ...scoreVars, decision: swDecision })
                      : null}
                  </p>
                </article>
              </div>
            </section>
          </>
        )}
      </section>
    </div>
  );
}
