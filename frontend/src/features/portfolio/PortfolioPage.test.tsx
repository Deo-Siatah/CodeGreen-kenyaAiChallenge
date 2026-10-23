import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { API } from '@/test/workflow-fixtures';
import { farmersList, statsOverview } from '@/test/stats-fixtures';
import { PortfolioPage } from './PortfolioPage';

function renderPortfolio() {
  return render(
    <MemoryRouter>
      <PortfolioPage />
    </MemoryRouter>,
  );
}

function mockPortfolio() {
  server.use(
    http.get(`${API}/api/stats/overview`, () => HttpResponse.json(statsOverview)),
    http.get(`${API}/api/farmers`, () => HttpResponse.json(farmersList)),
  );
}

describe('PortfolioPage', () => {
  it('renders the portfolio header, trust metrics, and scored farmers', async () => {
    mockPortfolio();
    renderPortfolio();

    expect(screen.getByRole('heading', { level: 1, name: /hifadhi/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /system dashboard/i })).toHaveAttribute(
      'href',
      '/ui',
    );
    expect(screen.getByRole('link', { name: /^new case$/i })).toHaveAttribute(
      'href',
      '/case/new',
    );
    expect(
      screen.getByRole('link', { name: /watch the recorded demo/i }),
    ).toHaveAttribute('href', '/replay');

    expect(await screen.findByTestId('metric-farmers')).toHaveTextContent('60');
    expect(screen.getByTestId('metric-scored')).toHaveTextContent('53');
    expect(screen.getByTestId('metric-repayment')).toHaveTextContent('71%');

    const grace = await screen.findByRole('link', { name: /grace wanjiku/i });
    expect(grace).toHaveAttribute('href', '/case/farmer-1');
    expect(screen.getByTestId('case-score-farmer-1')).toHaveTextContent('89.8');
    expect(screen.getByTestId('case-decision-farmer-1')).toHaveTextContent('Eligible');

    const mary = screen.getByRole('link', { name: /mary achieng/i });
    expect(mary).toHaveAttribute('href', '/case/farmer-3');
    expect(screen.getByTestId('case-score-farmer-3')).toHaveTextContent('Unscored');
  });

  it('filters the portfolio by search text', async () => {
    mockPortfolio();
    renderPortfolio();

    const search = await screen.findByRole('searchbox', { name: /search farmers/i });
    const user = userEvent.setup({ delay: null });
    await user.type(search, 'grace');

    expect(screen.getByRole('link', { name: /grace wanjiku/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /mary achieng/i })).not.toBeInTheDocument();
  });

  it('shows an empty state when no farmers exist', async () => {
    server.use(
      http.get(`${API}/api/stats/overview`, () => HttpResponse.json(statsOverview)),
      http.get(`${API}/api/farmers`, () =>
        HttpResponse.json({ total: 0, items: [] }),
      ),
    );
    renderPortfolio();

    expect(await screen.findByText(/no farmers yet/i)).toBeInTheDocument();
  });
});
