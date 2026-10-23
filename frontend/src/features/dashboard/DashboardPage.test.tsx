import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { API } from '@/test/workflow-fixtures';
import { statsOverview } from '@/test/stats-fixtures';
import { DashboardPage } from './DashboardPage';

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe('DashboardPage', () => {
  it('renders the score distribution, loan pipeline, and fairness guardrails', async () => {
    server.use(
      http.get(`${API}/api/stats/overview`, () => HttpResponse.json(statsOverview)),
    );
    renderDashboard();

    expect(
      await screen.findByRole('heading', { level: 1, name: /system dashboard/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^portfolio$/i })).toHaveAttribute('href', '/');

    expect(await screen.findByTestId('metric-mean-final')).toHaveTextContent('61.4');
    expect(screen.getByTestId('metric-repayment')).toHaveTextContent('71%');
    expect(screen.getByTestId('metric-disbursed')).toHaveTextContent('23,000');

    expect(screen.getByTestId('chart-bucket-75-100')).toHaveTextContent('9');
    expect(screen.getByTestId('chart-decision-eligible')).toHaveTextContent('27');
    expect(screen.getByTestId('loan-status-repaid')).toHaveTextContent('5');
    expect(screen.getByTestId('component-testimony_pool')).toHaveTextContent('64.2');

    expect(screen.getByText(/fairness guardrails/i)).toBeInTheDocument();
    expect(screen.getByText(/ethnicity/i)).toBeInTheDocument();
    expect(screen.getByText(/capacity coverage/i)).toBeInTheDocument();
    expect(screen.getByTestId('scatter-plot')).toBeInTheDocument();
    expect(screen.getByTestId('case-row-farmer-1')).toHaveTextContent('Grace Wanjiku');
  });
});
