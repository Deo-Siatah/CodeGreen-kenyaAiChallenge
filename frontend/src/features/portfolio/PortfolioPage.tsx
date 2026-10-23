import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '@/api/errors';
import { listFarmers } from '@/api/endpoints/farmers';
import type { FarmerResponse } from '@/api/schemas';
import { ProductHeader } from '@/components/ProductHeader';
import {
  decisionTone,
  formatCount,
  formatMoney,
  formatPercent,
  formatScore,
} from '@/lib/format';
import { useI18n } from '@/i18n';
import { decisionLabel, loanStatusLabel } from '@/i18n/labels';
import { useStatsOverview } from '@/features/dashboard/useStatsOverview';
import './portfolio.css';

type FarmersStatus = 'loading' | 'ready' | 'error';

function usePortfolioFarmers() {
  const { t } = useI18n();
  const [items, setItems] = useState<FarmerResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<FarmersStatus>('loading');
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setStatus('loading');
    setError(null);

    void listFarmers({ limit: 100, offset: 0 }, controller.signal)
      .then((page) => {
        setItems(page.items);
        setTotal(page.total);
        setStatus('ready');
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.kind === 'cancelled') {
          return;
        }
        setStatus('error');
        setError(err instanceof ApiError ? err.message : t('portfolio.error.loadFarmers'));
      });

    return () => controller.abort();
  }, [attempt, t]);

  return {
    items,
    total,
    status,
    error,
    reload: () => setAttempt((value) => value + 1),
  };
}

export function PortfolioPage() {
  const { t } = useI18n();
  const stats = useStatsOverview();
  const farmers = usePortfolioFarmers();
  const [query, setQuery] = useState('');

  const loanStatusById = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of stats.data?.recent_cases ?? []) {
      if (item.loan_status) {
        map.set(item.id, item.loan_status);
      }
    }
    return map;
  }, [stats.data]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) {
      return farmers.items;
    }
    return farmers.items.filter((farmer) => {
      const county = farmer.county?.toLowerCase() ?? '';
      return (
        farmer.full_name.toLowerCase().includes(needle) ||
        county.includes(needle)
      );
    });
  }, [farmers.items, query]);

  return (
    <div className="portfolio-page">
      <ProductHeader active="portfolio" />
      <main className="portfolio-main">
        <section className="portfolio-hero" aria-labelledby="portfolio-title">
          <div>
            <p className="portfolio-eyebrow">{t('portfolio.eyebrow')}</p>
            <h1 id="portfolio-title" className="portfolio-title">
              Hifadhi
            </h1>
            <p className="portfolio-lead">{t('portfolio.lead')}</p>
          </div>
          <div className="portfolio-hero__actions">
            <Link className="portfolio-action portfolio-action--primary" to="/replay">
              {t('portfolio.action.demo')}
            </Link>
            <Link className="portfolio-action" to="/case/new">
              {t('portfolio.action.newCase')}
            </Link>
            <Link className="portfolio-action" to="/ui">
              {t('portfolio.action.inspect')}
            </Link>
          </div>
        </section>

        <section className="portfolio-metrics" aria-label={t('portfolio.summaryAria')}>
          {stats.status === 'loading' ? (
            <p className="portfolio-status">{t('portfolio.loading')}</p>
          ) : stats.status === 'error' ? (
            <div className="portfolio-error" role="alert">
              <span>{stats.error}</span>
              <button type="button" onClick={stats.reload}>
                {t('common.retry')}
              </button>
            </div>
          ) : stats.data ? (
            <>
              <article className="portfolio-metric">
                <span className="portfolio-metric__label">
                  {t('portfolio.metric.farmers')}
                </span>
                <strong className="portfolio-metric__value" data-testid="metric-farmers">
                  {formatCount(stats.data.farmers.total)}
                </strong>
                <span className="portfolio-metric__note">
                  {t('portfolio.metrics.counties', {
                    count: stats.data.farmers.counties.length,
                  })}
                </span>
              </article>
              <article className="portfolio-metric">
                <span className="portfolio-metric__label">
                  {t('portfolio.metric.scored')}
                </span>
                <strong className="portfolio-metric__value" data-testid="metric-scored">
                  {formatCount(stats.data.farmers.scored)}
                </strong>
                <span className="portfolio-metric__note">
                  {t('portfolio.metrics.awaiting', {
                    count: formatCount(stats.data.farmers.unscored),
                  })}
                </span>
              </article>
              <article className="portfolio-metric">
                <span className="portfolio-metric__label">
                  {t('portfolio.metric.mean')}
                </span>
                <strong className="portfolio-metric__value">
                  {formatScore(stats.data.scores.mean_final)}
                </strong>
                <span className="portfolio-metric__note">
                  {t('portfolio.metrics.axes', {
                    character: formatScore(stats.data.scores.mean_character),
                    capacity: formatScore(stats.data.scores.mean_capacity),
                  })}
                </span>
              </article>
              <article className="portfolio-metric">
                <span className="portfolio-metric__label">
                  {t('portfolio.metric.repayment')}
                </span>
                <strong className="portfolio-metric__value" data-testid="metric-repayment">
                  {formatPercent(stats.data.loans.repayment_rate)}
                </strong>
                <span className="portfolio-metric__note">
                  {t('portfolio.metrics.repaidOfDisbursed', {
                    repaid: formatMoney(stats.data.loans.repaid_amount),
                    disbursed: formatMoney(stats.data.loans.disbursed_amount),
                  })}
                </span>
              </article>
            </>
          ) : null}
        </section>

        <section className="portfolio-list" aria-labelledby="farmers-title">
          <div className="portfolio-list__head">
            <div>
              <h2 id="farmers-title">{t('portfolio.list.title')}</h2>
              <p>
                {farmers.status === 'ready'
                  ? t('portfolio.list.cases', {
                      shown: filtered.length,
                      total: farmers.total,
                    })
                  : t('portfolio.list.loading')}
              </p>
            </div>
            <label className="portfolio-search">
              <span className="sr-only">{t('portfolio.list.search')}</span>
              <input
                type="search"
                aria-label={t('portfolio.list.search')}
                placeholder={t('portfolio.list.searchPlaceholder')}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
          </div>

          {farmers.status === 'loading' ? (
            <p className="portfolio-status">{t('common.loading')}</p>
          ) : farmers.status === 'error' ? (
            <div className="portfolio-error" role="alert">
              <span>{farmers.error}</span>
              <button type="button" onClick={farmers.reload}>
                {t('common.retry')}
              </button>
            </div>
          ) : farmers.items.length === 0 ? (
            <div className="portfolio-empty">
              <h3>{t('portfolio.list.emptyTitle')}</h3>
              <p>{t('portfolio.list.emptyBody')}</p>
              <Link className="portfolio-action portfolio-action--primary" to="/case/new">
                {t('portfolio.list.emptyAction')}
              </Link>
            </div>
          ) : filtered.length === 0 ? (
            <p className="portfolio-status">
              {t('portfolio.list.noMatch', { query })}
            </p>
          ) : (
            <ul className="portfolio-rows">
              {filtered.map((farmer) => {
                const score = farmer.current_score;
                const loanStatus = loanStatusById.get(farmer.id) ?? null;
                return (
                  <li key={farmer.id}>
                    <Link className="portfolio-row" to={`/case/${farmer.id}`}>
                      <div className="portfolio-row__identity">
                        <span className="portfolio-row__name">{farmer.full_name}</span>
                        <span className="portfolio-row__county">
                          {farmer.county ?? t('common.countyUnknown')}
                        </span>
                      </div>
                      <div
                        className="portfolio-row__score"
                        data-testid={`case-score-${farmer.id}`}
                      >
                        {score ? formatScore(score.final_score) : t('common.unscored')}
                      </div>
                      <span
                        className="portfolio-row__decision"
                        data-tone={decisionTone(score?.decision ?? null)}
                        data-testid={`case-decision-${farmer.id}`}
                      >
                        {decisionLabel(score?.decision, t)}
                      </span>
                      <span className="portfolio-row__amount">
                        {score?.recommended_amount
                          ? `KES ${formatMoney(score.recommended_amount)}`
                          : t('common.noOffer')}
                      </span>
                      <span className="portfolio-row__loan">
                        {loanStatus
                          ? loanStatusLabel(loanStatus, t)
                          : t('common.noLoan')}
                      </span>
                      <span className="portfolio-row__open" aria-hidden="true">
                        →
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
      <footer className="portfolio-footer">
        <span>{t('portfolio.footer.line1')}</span>
        <span>{t('portfolio.footer.line2')}</span>
      </footer>
    </div>
  );
}
