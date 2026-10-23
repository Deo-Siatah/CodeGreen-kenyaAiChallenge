import type { ScoreProfileResponse } from '@/api/schemas';
import { useI18n } from '@/i18n';
import { decisionLabel } from '@/i18n/labels';

function formatScore(value: number): string {
  return value.toFixed(1);
}

function formatAmount(
  value: number | null,
  locale: string,
  t: ReturnType<typeof useI18n>['t'],
): string {
  if (value === null) {
    return t('common.notRecommended');
  }
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'KES',
    maximumFractionDigits: 0,
  }).format(value);
}

export function ScoreCard({ profile }: { profile: ScoreProfileResponse }) {
  const { t, locale } = useI18n();

  return (
    <section className="score-card" aria-label={t('score.cardAria')} data-testid="score-card">
      <div className="score-card__headline">
        <span className="score-card__label">{t('score.final')}</span>
        <strong className="score-card__final" data-testid="score-final">
          {formatScore(profile.final_score)}
        </strong>
        <span className="score-card__decision" data-decision={profile.decision ?? 'none'}>
          {decisionLabel(profile.decision, t)}
        </span>
      </div>

      <dl className="score-card__axes">
        <div>
          <dt>{t('score.character')}</dt>
          <dd data-testid="score-character">{formatScore(profile.character_score)}</dd>
        </div>
        <div>
          <dt>{t('score.capacity')}</dt>
          <dd data-testid="score-capacity">
            {profile.capacity_score === null
              ? t('score.noSatellite')
              : formatScore(profile.capacity_score)}
          </dd>
        </div>
        <div>
          <dt>{t('score.recommended')}</dt>
          <dd data-testid="score-amount">
            {formatAmount(profile.recommended_amount, locale, t)}
          </dd>
        </div>
      </dl>

      <p className="score-card__version">
        {t('score.version', { version: profile.version })}
      </p>
    </section>
  );
}
