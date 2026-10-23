import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph } from '@/test/case-harness';
import { API } from '@/test/workflow-fixtures';
import { useGraphStore } from '@/features/graph/store';

const networkBody = {
  farmer: { id: 'farmer-1', full_name: 'Ann Wanjiku', county: 'Nakuru' },
  farms: [{ id: 'farm-1', acreage: 2.5, latitude: -0.3, longitude: 36.1 }],
  trust_sources: [
    {
      id: 'ts-1',
      name: 'Kariuki Mwangi',
      category: 'administrative official',
      phone_masked: '07******11',
      credibility_score: 1,
    },
  ],
  market_actors: [],
  social_groups: [],
  latest_session: null,
  current_score: {
    id: 'sp-1',
    character_score: 71.25,
    capacity_score: 63,
    final_score: 68,
    decision: 'ELIGIBLE',
    recommended_amount: 15000,
  },
  loans: [],
};

const pendingLoan = {
  id: 'loan-1',
  farmer_id: 'farmer-1',
  amount: 15000,
  purpose: 'Seed and fertiliser',
  duration_months: 6,
  interest_rate: 10,
  status: 'pending_disbursement',
  applied_at: '2026-10-19T09:00:00Z',
  approved_at: null,
  disbursed_at: null,
  due_date: null,
  repaid_at: null,
  defaulted_at: null,
  score_profile_id: 'sp-1',
};

const disbursedLoan = {
  ...pendingLoan,
  status: 'disbursed',
  disbursed_at: '2026-10-19T09:05:00Z',
};

const repaidLoan = {
  ...disbursedLoan,
  status: 'repaid',
  repaid_at: '2026-10-19T09:10:00Z',
};

async function openLoanStep() {
  server.use(
    http.get(`${API}/api/farmers/farmer-1/network`, () => HttpResponse.json(networkBody)),
    http.get(`${API}/api/loans`, () => HttpResponse.json([])),
  );

  renderCase('/case/farmer-1');
  const user = userEvent.setup({ delay: null });
  await user.click(await screen.findByRole('button', { name: /^6 loan$/i }));
  await screen.findByRole('button', { name: /create loan/i });
  return user;
}

afterEach(() => {
  resetGraph();
});

describe('Step 6 — Loan', () => {
  it('creates a loan, disburses it, and records repayment with graph events', async () => {
    let created: unknown = null;
    const disbursedIds: string[] = [];
    const repaidIds: string[] = [];

    server.use(
      http.post(`${API}/api/loans`, async ({ request }) => {
        created = await request.json();
        return HttpResponse.json(pendingLoan, { status: 201 });
      }),
      http.post(`${API}/api/loans/loan-1/disburse`, () => {
        disbursedIds.push('loan-1');
        return HttpResponse.json(disbursedLoan);
      }),
      http.post(`${API}/api/loans/loan-1/repay`, () => {
        repaidIds.push('loan-1');
        return HttpResponse.json(repaidLoan);
      }),
    );

    const user = await openLoanStep();

    expect(screen.getByTestId('loan-recommendation')).toHaveTextContent('15,000');
    await user.type(screen.getByLabelText(/amount/i), '15000');
    await user.type(screen.getByLabelText(/purpose/i), 'Seed and fertiliser');
    await user.type(screen.getByLabelText(/duration/i), '6');
    await user.type(screen.getByLabelText(/interest/i), '10');
    await user.click(screen.getByRole('button', { name: /create loan/i }));

    await screen.findByTestId('loan-row');
    expect(created).toEqual({
      farmer_id: 'farmer-1',
      amount: 15000,
      purpose: 'Seed and fertiliser',
      duration_months: 6,
      interest_rate: 10,
    });
    expect(screen.getByText('Pending disbursement')).toBeInTheDocument();
    expect(useGraphStore.getState().nodes['loan-1']?.meta.status).toBe('pending_disbursement');

    await user.click(screen.getByRole('button', { name: /^disburse$/i }));
    await waitFor(() => expect(disbursedIds).toEqual(['loan-1']));
    expect(await screen.findByText('Disbursed')).toBeInTheDocument();
    expect(useGraphStore.getState().nodes['loan-1']?.meta.status).toBe('disbursed');

    await user.click(screen.getByRole('button', { name: /mark repaid/i }));
    await waitFor(() => expect(repaidIds).toEqual(['loan-1']));
    expect(await screen.findByText('Repaid')).toBeInTheDocument();
    expect(useGraphStore.getState().nodes['loan-1']?.meta.status).toBe('repaid');
  });

  it('shows the backend reason when a loan is rejected', async () => {
    server.use(
      http.post(`${API}/api/loans`, () =>
        HttpResponse.json(
          { detail: 'Loan amount 20000 exceeds recommended amount 15000' },
          { status: 422 },
        ),
      ),
    );

    const user = await openLoanStep();
    await user.type(screen.getByLabelText(/amount/i), '20000');
    await user.click(screen.getByRole('button', { name: /create loan/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('exceeds recommended amount');
  });
});
