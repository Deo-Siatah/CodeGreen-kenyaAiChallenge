import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '@/api/errors';
import { getStatsOverview } from '@/api/endpoints/stats';
import type { StatsOverviewResponse } from '@/api/schemas';
import { useI18n } from '@/i18n';

export type StatsStatus = 'loading' | 'ready' | 'error';

export function useStatsOverview() {
  const { t } = useI18n();
  const [data, setData] = useState<StatsOverviewResponse | null>(null);
  const [status, setStatus] = useState<StatsStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  const reload = useCallback(() => {
    setAttempt((value) => value + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setStatus('loading');
    setError(null);

    void getStatsOverview(controller.signal)
      .then((overview) => {
        setData(overview);
        setStatus('ready');
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.kind === 'cancelled') {
          return;
        }
        setStatus('error');
        setError(err instanceof ApiError ? err.message : t('dashboard.error.load'));
      });

    return () => controller.abort();
  }, [attempt, t]);

  return { data, status, error, reload };
}
