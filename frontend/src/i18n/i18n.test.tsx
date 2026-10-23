import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { API } from '@/test/workflow-fixtures';
import { statsOverview } from '@/test/stats-fixtures';
import { I18nProvider, translate, useI18n } from './index';
import { LanguageToggle } from './LanguageToggle';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { PortfolioPage } from '@/features/portfolio/PortfolioPage';
import { renderCase, resetGraph } from '@/test/case-harness';

function Probe() {
  const { t, language } = useI18n();
  return (
    <div>
      <span data-testid="language">{language}</span>
      <span data-testid="farmers">{t('portfolio.metric.farmers')}</span>
      <span data-testid="interpolated">{t('portfolio.metrics.counties', { count: 3 })}</span>
    </div>
  );
}

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.lang = '';
  resetGraph();
});

describe('i18n', () => {
  it('defaults to English and interpolates values', () => {
    render(
      <I18nProvider>
        <Probe />
      </I18nProvider>,
    );

    expect(screen.getByTestId('language')).toHaveTextContent('en');
    expect(screen.getByTestId('farmers')).toHaveTextContent('Farmers');
    expect(screen.getByTestId('interpolated')).toHaveTextContent('across 3 counties');
    expect(document.documentElement.lang).toBe('en');
  });

  it('translates simple helpers without React', () => {
    expect(translate('sw', 'portfolio.metric.farmers')).toBe('Wakulima');
    expect(translate('sw', 'portfolio.metrics.counties', { count: 4 })).toBe(
      'katika kaunti 4',
    );
    expect(translate('en', 'portfolio.metrics.counties', { count: 1 })).toBe(
      'across 1 county',
    );
  });

  it('switches to Kiswahili, persists it, and updates the document language', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <I18nProvider>
        <LanguageToggle />
        <Probe />
      </I18nProvider>,
    );

    await user.click(screen.getByRole('button', { name: /switch to kiswahili/i }));

    expect(screen.getByTestId('language')).toHaveTextContent('sw');
    expect(screen.getByTestId('farmers')).toHaveTextContent('Wakulima');
    expect(window.localStorage.getItem('hifadhi.language')).toBe('sw');
    expect(document.documentElement.lang).toBe('sw');
  });

  it('renders the dashboard in Kiswahili when initialised that way', async () => {
    server.use(
      http.get(`${API}/api/stats/overview`, () => HttpResponse.json(statsOverview)),
    );

    render(
      <I18nProvider initialLanguage="sw">
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </I18nProvider>,
    );

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashibodi ya mfumo' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Hatimiliki ya haki')).toBeInTheDocument();
    expect(screen.getByText('Wastani wa alama za mwisho')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Wakulima' })).toHaveAttribute('href', '/');
  });

  it('translates the case workflow and toggles back to English', async () => {
    const user = userEvent.setup({ delay: null });
    renderCase('/case/new', { language: 'sw' });

    expect(await screen.findByText('Taarifa za mkulima')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^1 mkulima$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/jina kamili/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', { name: /badilisha lugha kuwa kiingereza/i }),
    );

    expect(await screen.findByText('Farmer details')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^1 farmer$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
  });

  it('renders the portfolio in Kiswahili when initialised that way', async () => {
    server.use(
      http.get(`${API}/api/stats/overview`, () => HttpResponse.json(statsOverview)),
      http.get(`${API}/api/farmers`, () =>
        HttpResponse.json({
          total: 1,
          items: [
            {
              id: 'farmer-1',
              full_name: 'Grace Wanjiku',
              county: 'Nakuru',
              created_at: '2026-10-22T08:00:00Z',
              current_score: {
                final_score: 89.8,
                decision: 'ELIGIBLE',
                recommended_amount: 5000,
              },
            },
          ],
        }),
      ),
    );

    render(
      <I18nProvider initialLanguage="sw">
        <MemoryRouter>
          <PortfolioPage />
        </MemoryRouter>
      </I18nProvider>,
    );

    expect(screen.getByText('Miundombinu ya uaminifu wa jamii')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /dashibodi ya mfumo/i })).toHaveAttribute(
      'href',
      '/ui',
    );
    expect(screen.getByRole('searchbox', { name: /tafuta wakulima/i })).toHaveAttribute(
      'placeholder',
      'Tafuta jina au kaunti',
    );
    expect(await screen.findByTestId('metric-farmers')).toHaveTextContent('60');
    expect(screen.getByText('Wakulima', { selector: '.portfolio-metric__label' })).toBeInTheDocument();
    expect(screen.getByText('Waliopimwa')).toBeInTheDocument();
    expect(screen.getByText('Marejesho')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: /grace wanjiku/i })).toBeInTheDocument();
  });
});
