import { Link } from 'react-router-dom';
import type { ScatterPoint } from '@/api/schemas';
import { ProductHeader } from '@/components/ProductHeader';
import {
  decisionTone,
  formatCount,
  formatMoney,
  formatPercent,
  formatScore,
} from '@/lib/format';
import { useI18n } from '@/i18n';
import {
  componentLabel,
  decisionLabel,
  excludedInputLabel,
  genderLabel,
  loanStatusLabel,
} from '@/i18n/labels';
import { useStatsOverview } from './useStatsOverview';
import './dashboard.css';

const LOAN_STATUSES = [
  'pending_disbursement',
  'disbursed',
  'repaid',
  'defaulted',
] as const;

function ScatterPlot({ points }: { points: ScatterPoint[] }) {
  const { t } = useI18n();
  const maxAcreage = Math.max(1, ...points.map((point) => point.acreage));
  return (
    <svg
      className="dash-scatter"
      viewBox="0 0 100 62"
      role="img"
      aria-label={t('dashboard.fairness.scatterAria')}
      data-testid="scatter-plot"
    >
      {[10, 25, 40, 55].map((y) => (
        <line key={y} x1="8" x2="96" y1={y} y2={y} className="dash-scatter__grid" />
      ))}
      <line x1="8" x2="96" y1="58" y2="58" className="dash-scatter__axis" />
      <line x1="8" x2="8" y1="6" y2="58" className="dash-scatter__axis" />
      {points.map((point) => {
        const x = 8 + (point.acreage / maxAcreage) * 86;
        const y = 58 - (point.final_score / 100) * 52;
        return (
          <circle
            key={`${point.acreage}-${point.final_score}`}
            cx={x}
            cy={y}
            r="1.7"
            className="dash-scatter__dot"
          />
        );
      })}
      <text x="52" y="61.5" className="dash-scatter__label">
        {t('common.acres')}
      </text>
      <text x="2" y="8" className="dash-scatter__label">
        {t('common.score')}
      </text>
    </svg>
  );
}

export function DashboardPage() {
  const { t, locale } = useI18n();
  const { data, status, error, reload } = useStatsOverview();

  if (status === 'loading') {
    return (
      <div className="dash-page">
        <ProductHeader active="dashboard" />
        <main className="dash-main">
          <p className="dash-status">{t('dashboard.loading')}</p>
        </main>
      </div>
    );
  }

  if (status === 'error' || !data) {
    return (
      <div className="dash-page">
        <ProductHeader active="dashboard" />
        <main className="dash-main">
          <div className="dash-error" role="alert">
            <p>{error ?? t('dashboard.error.load')}</p>
            <button type="button" onClick={reload}>
              {t('common.retry')}
            </button>
          </div>
        </main>
      </div>
    );
  }

  const maxBucket = Math.max(1, ...data.scores.buckets.map((bucket) => bucket.count));
  const decisionTotal = Math.max(
    1,
    data.scores.decisions.eligible +
      data.scores.decisions.review_required +
      data.scores.decisions.decline +
      data.scores.decisions.unscored,
  );
  const eligibleShare = (data.scores.decisions.eligible / decisionTotal) * 100;
  const reviewShare = eligibleShare + (data.scores.decisions.review_required / decisionTotal) * 100;
  const declineShare = reviewShare + (data.scores.decisions.decline / decisionTotal) * 100;
  const countyMax = Math.max(1, ...data.farmers.counties.map((county) => county.count));

  return (
    <div className="dash-page">
      <ProductHeader active="dashboard" />
      <main className="dash-main">
        <header className="dash-intro">
          <div>
            <p className="dash-eyebrow">{t('dashboard.eyebrow')}</p>
            <h1>{t('dashboard.title')}</h1>
            <p>{t('dashboard.lead')}</p>
          </div>
          <span className="dash-generated">
            {t('dashboard.snapshot', {
              date: new Date(data.generated_at).toLocaleString(locale),
            })}
          </span>
        </header>

        <section className="dash-metrics" aria-label={t('dashboard.metrics.aria')}>
          <article className="dash-metric">
            <span>{t('dashboard.metric.farmers')}</span>
            <strong>{formatCount(data.farmers.total)}</strong>
            <small>
              {t('dashboard.metric.counties', {
                count: data.farmers.counties.length,
              })}
            </small>
          </article>
          <article className="dash-metric">
            <span>{t('dashboard.metric.mean')}</span>
            <strong data-testid="metric-mean-final">
              {formatScore(data.scores.mean_final)}
            </strong>
            <small>
              {t('dashboard.metric.axes', {
                character: formatScore(data.scores.mean_character),
                capacity: formatScore(data.scores.mean_capacity),
              })}
            </small>
          </article>
          <article className="dash-metric">
            <span>{t('dashboard.metric.repaymentRate')}</span>
            <strong data-testid="metric-repayment">
              {formatPercent(data.loans.repayment_rate)}
            </strong>
            <small>
              {t('dashboard.metric.repaidDefaulted', {
                repaid: data.loans.repaid,
                defaulted: data.loans.defaulted,
              })}
            </small>
          </article>
          <article className="dash-metric">
            <span>{t('dashboard.metric.disbursed')}</span>
            <strong data-testid="metric-disbursed">
              {formatMoney(data.loans.disbursed_amount)}
            </strong>
            <small>
              {t('dashboard.metric.loans', { count: data.loans.total })}
            </small>
          </article>
        </section>

        <div className="dash-grid">
          <section className="dash-panel dash-panel--wide" aria-labelledby="distribution-title">
            <header>
              <h2 id="distribution-title">{t('dashboard.distribution.title')}</h2>
              <p>{t('dashboard.distribution.note')}</p>
            </header>
            <div className="dash-bars" role="list">
              {data.scores.buckets.map((bucket) => (
                <div
                  className="dash-bar"
                  role="listitem"
                  key={bucket.label}
                  data-testid={`chart-bucket-${bucket.label}`}
                >
                  <span className="dash-bar__value">{bucket.count}</span>
                  <span
                    className="dash-bar__fill"
                    style={{ height: `${Math.max(4, (bucket.count / maxBucket) * 100)}%` }}
                  />
                  <span className="dash-bar__label">{bucket.label}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="dash-panel" aria-labelledby="decisions-title">
            <header>
              <h2 id="decisions-title">{t('dashboard.decisions.title')}</h2>
              <p>{t('dashboard.decisions.note')}</p>
            </header>
            <div className="dash-decisions">
              <div
                className="dash-donut"
                style={{
                  background: `conic-gradient(
                    hsl(var(--decision-good)) 0 ${eligibleShare}%,
                    hsl(var(--decision-warn)) ${eligibleShare}% ${reviewShare}%,
                    hsl(var(--decision-bad)) ${reviewShare}% ${declineShare}%,
                    hsl(var(--muted)) ${declineShare}% 100%
                  )`,
                }}
                aria-hidden="true"
              >
                <span>{data.scores.scored}</span>
              </div>
              <dl className="dash-legend">
                <div>
                  <dt>
                    <i data-tone="good" /> {t('dashboard.legend.eligible')}
                  </dt>
                  <dd data-testid="chart-decision-eligible">
                    {data.scores.decisions.eligible}
                  </dd>
                </div>
                <div>
                  <dt>
                    <i data-tone="warn" /> {t('dashboard.legend.review')}
                  </dt>
                  <dd data-testid="chart-decision-review">
                    {data.scores.decisions.review_required}
                  </dd>
                </div>
                <div>
                  <dt>
                    <i data-tone="bad" /> {t('dashboard.legend.decline')}
                  </dt>
                  <dd data-testid="chart-decision-decline">
                    {data.scores.decisions.decline}
                  </dd>
                </div>
                <div>
                  <dt>
                    <i data-tone="muted" /> {t('dashboard.legend.unscored')}
                  </dt>
                  <dd data-testid="chart-decision-unscored">
                    {data.scores.decisions.unscored}
                  </dd>
                </div>
              </dl>
            </div>
          </section>

          <section className="dash-panel" aria-labelledby="components-title">
            <header>
              <h2 id="components-title">{t('dashboard.components.title')}</h2>
              <p>{t('dashboard.components.note')}</p>
            </header>
            <ul className="dash-components">
              {data.components.map((component) => (
                <li
                  key={component.component_name}
                  data-testid={`component-${component.component_name}`}
                >
                  <div>
                    <span>{componentLabel(component.component_name, t)}</span>
                    <small>
                      {t('dashboard.components.sample', {
                        count: component.sample_size,
                      })}
                    </small>
                  </div>
                  <span className="dash-track">
                    <span
                      className="dash-track__fill"
                      style={{ width: `${Math.min(100, component.mean_contribution)}%` }}
                    />
                  </span>
                  <strong>{formatScore(component.mean_contribution)}</strong>
                </li>
              ))}
            </ul>
          </section>

          <section className="dash-panel" aria-labelledby="loans-title">
            <header>
              <h2 id="loans-title">{t('dashboard.loans.title')}</h2>
              <p>{t('dashboard.loans.note')}</p>
            </header>
            <dl className="dash-loans">
              {LOAN_STATUSES.map((loanStatus) => {
                const value =
                  loanStatus === 'pending_disbursement'
                    ? data.loans.pending_disbursement
                    : loanStatus === 'disbursed'
                      ? data.loans.disbursed
                      : loanStatus === 'repaid'
                        ? data.loans.repaid
                        : data.loans.defaulted;
                const amount =
                  loanStatus === 'repaid'
                    ? data.loans.repaid_amount
                    : loanStatus === 'defaulted'
                      ? data.loans.defaulted_amount
                      : loanStatus === 'disbursed'
                        ? data.loans.disbursed_amount
                        : null;
                return (
                  <div key={loanStatus} data-testid={`loan-status-${loanStatus}`}>
                    <dt>{loanStatusLabel(loanStatus, t)}</dt>
                    <dd>{value}</dd>
                    <small>{amount === null ? '—' : `KES ${formatMoney(amount)}`}</small>
                  </div>
                );
              })}
            </dl>
          </section>

          <section className="dash-panel" aria-labelledby="network-title">
            <header>
              <h2 id="network-title">{t('dashboard.network.title')}</h2>
              <p>{t('dashboard.network.note')}</p>
            </header>
            <dl className="dash-network">
              <div>
                <dt>{t('dashboard.network.trustSources')}</dt>
                <dd>{formatCount(data.network.trust_sources)}</dd>
              </div>
              <div>
                <dt>{t('dashboard.network.marketActors')}</dt>
                <dd>{formatCount(data.network.market_actors)}</dd>
              </div>
              <div>
                <dt>{t('dashboard.network.socialGroups')}</dt>
                <dd>{formatCount(data.network.social_groups)}</dd>
              </div>
              <div>
                <dt>{t('dashboard.network.links')}</dt>
                <dd>{formatCount(data.network.links)}</dd>
              </div>
              <div>
                <dt>{t('dashboard.network.sessions')}</dt>
                <dd>{formatCount(data.network.sessions)}</dd>
              </div>
              <div>
                <dt>{t('dashboard.network.responseRate')}</dt>
                <dd>{formatPercent(data.network.response_rate)}</dd>
              </div>
            </dl>
          </section>

          <section className="dash-panel dash-panel--wide" aria-labelledby="fairness-title">
            <header>
              <h2 id="fairness-title">{t('dashboard.fairness.title')}</h2>
              <p>{t('dashboard.fairness.note')}</p>
            </header>
            <div className="dash-fairness">
              <div>
                <h3>{t('dashboard.fairness.excluded')}</h3>
                <ul className="dash-chips">
                  {data.fairness.excluded_inputs.map((input) => (
                    <li key={input}>{excludedInputLabel(input, t)}</li>
                  ))}
                </ul>
                <h3>{t('dashboard.fairness.axisWeights')}</h3>
                <p className="dash-axis">
                  {t('dashboard.fairness.character')}{' '}
                  <strong>{formatPercent(data.fairness.character_axis_weight)}</strong>
                  <span />
                  {t('dashboard.fairness.capacity')}{' '}
                  <strong>{formatPercent(data.fairness.capacity_axis_weight)}</strong>
                </p>
                <h3>{t('dashboard.fairness.coverage')}</h3>
                <p className="dash-coverage">
                  {t('dashboard.fairness.coverageDetail', {
                    percent: formatPercent(data.fairness.capacity_coverage),
                  })}
                </p>
                <h3>{t('dashboard.fairness.acreage')}</h3>
                <p className="dash-coverage">
                  {data.fairness.acreage_score_correlation === null
                    ? '—'
                    : t('dashboard.fairness.correlation', {
                        value: data.fairness.acreage_score_correlation.toFixed(2),
                      })}
                </p>
                <ScatterPlot points={data.fairness.acreage_vs_score} />
              </div>
              <div>
                <h3>{t('dashboard.fairness.gender')}</h3>
                <table className="dash-table dash-table--compact">
                  <thead>
                    <tr>
                      <th>{t('dashboard.table.group')}</th>
                      <th>{t('dashboard.table.count')}</th>
                      <th>{t('dashboard.table.meanFinal')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.fairness.gender.map((row) => (
                      <tr key={row.gender}>
                        <td>{genderLabel(row.gender, t)}</td>
                        <td>{row.count}</td>
                        <td>{formatScore(row.mean_final)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <h3>{t('dashboard.fairness.counties')}</h3>
                <ul className="dash-counties">
                  {data.farmers.counties.slice(0, 6).map((county) => (
                    <li key={county.county ?? 'unknown'}>
                      <span>{county.county ?? t('common.unknown')}</span>
                      <span className="dash-track">
                        <span
                          className="dash-track__fill"
                          style={{ width: `${(county.count / countyMax) * 100}%` }}
                        />
                      </span>
                      <strong>{county.count}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        </div>

        <section className="dash-panel" aria-labelledby="recent-title">
          <header>
            <h2 id="recent-title">{t('dashboard.recent.title')}</h2>
            <p>{t('dashboard.recent.note')}</p>
          </header>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>{t('dashboard.table.farmer')}</th>
                  <th>{t('dashboard.table.county')}</th>
                  <th>{t('dashboard.table.score')}</th>
                  <th>{t('dashboard.table.decision')}</th>
                  <th>{t('dashboard.table.offer')}</th>
                  <th>{t('dashboard.table.loan')}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {data.recent_cases.map((item) => (
                  <tr key={item.id} data-testid={`case-row-${item.id}`}>
                    <td>{item.full_name}</td>
                    <td>{item.county ?? '—'}</td>
                    <td className="dash-mono">{formatScore(item.final_score)}</td>
                    <td>
                      <span
                        className="dash-decision"
                        data-tone={decisionTone(item.decision)}
                      >
                        {decisionLabel(item.decision, t)}
                      </span>
                    </td>
                    <td className="dash-mono">
                      {item.recommended_amount === null
                        ? '—'
                        : `KES ${formatMoney(item.recommended_amount)}`}
                    </td>
                    <td>{loanStatusLabel(item.loan_status, t)}</td>
                    <td>
                      <Link className="dash-open" to={`/case/${item.id}`}>
                        {t('common.open')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
