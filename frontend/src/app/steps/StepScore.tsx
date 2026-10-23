import { useEffect, useState } from 'react';
import type { BreakdownResponse, ScoreProfileResponse } from '@/api/schemas';
import { schemas } from '@/api/schemas';
import { ApiError } from '@/api/errors';
import { getVerificationBreakdown, getVerificationResult } from '@/api/endpoints/verification';
import type { Decision } from '@/domain/graph';
import { useGraphStore } from '@/features/graph/store';
import { useI18n } from '@/i18n';
import { Breakdown } from './Breakdown';
import { ExplanationPanel } from './ExplanationPanel';
import { ScoreCard } from './ScoreCard';

function toDecision(value: string | null): Decision | null {
  return value === 'ELIGIBLE' || value === 'REVIEW_REQUIRED' || value === 'DECLINE' ? value : null;
}

export function StepScore() {
  const { t } = useI18n();
  const sessionId = useGraphStore((state) => state.sessionId);
  const dispatch = useGraphStore((state) => state.dispatch);

  const [profile, setProfile] = useState<ScoreProfileResponse | null>(null);
  const [breakdown, setBreakdown] = useState<BreakdownResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    void (async () => {
      try {
        const [result, scores] = await Promise.all([
          getVerificationResult(sessionId, controller.signal),
          getVerificationBreakdown(sessionId, controller.signal),
        ]);
        const parsed = schemas.ScoreProfileResponse.safeParse(result.score_profile);
        if (!parsed.success) {
          setError(t('case.score.invalid'));
          return;
        }
        setProfile(parsed.data);
        setBreakdown(scores);

        const decision = toDecision(parsed.data.decision);
        if (decision) {
          await dispatch([
            {
              type: 'SCORE_COMPUTED',
              score: {
                final: parsed.data.final_score,
                character: parsed.data.character_score,
                capacity: parsed.data.capacity_score,
                decision,
                recommendedAmount: parsed.data.recommended_amount,
              },
            },
          ]);
        }
      } catch (err) {
        if (err instanceof ApiError && err.kind === 'cancelled') {
          return;
        }
        if (err instanceof ApiError && err.kind === 'not_found') {
          setError(t('case.score.missing'));
          return;
        }
        setError(err instanceof ApiError ? err.message : t('case.score.error'));
      } finally {
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [sessionId, dispatch, t]);

  if (!sessionId) {
    return <p className="case-status">{t('case.score.noSession')}</p>;
  }

  return (
    <div className="case-score">
      {loading ? <p className="case-status">{t('case.score.loading')}</p> : null}
      {error ? (
        <p className="case-status" role="alert">
          {error}
        </p>
      ) : null}
      {profile ? <ScoreCard profile={profile} /> : null}
      {breakdown ? <Breakdown components={breakdown.components} axisNote={breakdown.axis_note} /> : null}
      <ExplanationPanel sessionId={sessionId} />
    </div>
  );
}
