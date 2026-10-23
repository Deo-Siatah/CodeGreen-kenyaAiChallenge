import { http, HttpResponse } from 'msw';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph } from '@/test/case-harness';
import { API, farmerRequestBody, farmerResponse } from '@/test/workflow-fixtures';
import { useGraphStore } from '@/features/graph/store';

const networkBody = {
  farmer: { id: 'farmer-1', full_name: 'Ann Wanjiku', county: 'Nakuru' },
  farms: [],
  trust_sources: [],
  market_actors: [],
  social_groups: [],
  latest_session: null,
  current_score: null,
  loans: [],
};

function mockNetwork() {
  server.use(http.get(`${API}/api/farmers/farmer-1/network`, () => HttpResponse.json(networkBody)));
}

async function fillFarmerForm() {
  const user = userEvent.setup({ delay: null });
  await user.type(screen.getByLabelText(/full name/i), 'Ann Wanjiku');
  await user.type(screen.getByLabelText(/national id/i), '12345678');
  await user.type(screen.getByLabelText(/^phone/i), '0712345678');
  await user.selectOptions(screen.getByLabelText(/gender/i), 'Female');
  await user.type(screen.getByLabelText(/date of birth/i), '1990-01-01');
  await user.type(screen.getByLabelText(/^location/i), 'Nakuru');
  await user.type(screen.getByLabelText(/^county/i), 'Nakuru');
  await user.selectOptions(screen.getByLabelText(/farming type/i), 'Crop');
  return user;
}

afterEach(() => {
  resetGraph();
});

describe('Step 1 — Farmer', () => {
  it('2. posts a body deep-equal to the input, dispatches FARMER_CREATED and navigates', async () => {
    let captured: unknown = null;
    server.use(
      http.post(`${API}/api/farmers`, async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(farmerResponse, { status: 201 });
      }),
    );
    mockNetwork();

    const { router } = renderCase('/case/new');
    const user = await fillFarmerForm();
    await user.click(screen.getByRole('button', { name: /create farmer/i }));

    await waitFor(() => expect(router.state.location.pathname).toBe('/case/farmer-1'));

    expect(captured).toEqual(farmerRequestBody);
    expect(Object.keys(captured as object).sort()).toEqual(
      Object.keys(farmerRequestBody).sort(),
    );
    await waitFor(() => expect(useGraphStore.getState().nodes['farmer-1']?.kind).toBe('farmer'));
  });

  it('3. a double click sends exactly one request', async () => {
    let count = 0;
    server.use(
      http.post(`${API}/api/farmers`, async () => {
        count += 1;
        return HttpResponse.json(farmerResponse, { status: 201 });
      }),
    );
    mockNetwork();

    renderCase('/case/new');
    const user = await fillFarmerForm();
    await user.dblClick(screen.getByRole('button', { name: /create farmer/i }));

    await waitFor(() => expect(count).toBe(1));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(count).toBe(1);
  });

  it('4. a 422 renders each backend field error beside its input', async () => {
    server.use(
      http.post(`${API}/api/farmers`, () =>
        HttpResponse.json(
          {
            detail: [
              { loc: ['body', 'full_name'], msg: 'full name is required', type: 'missing' },
              { loc: ['body', 'phone'], msg: 'phone is invalid', type: 'value_error' },
            ],
          },
          { status: 422 },
        ),
      ),
    );

    renderCase('/case/new');
    const user = await fillFarmerForm();
    await user.click(screen.getByRole('button', { name: /create farmer/i }));

    expect(await screen.findByText('full name is required')).toBeInTheDocument();
    expect(screen.getByText('phone is invalid')).toBeInTheDocument();
  });

  it('5. a 500 renders an Alert whose retry re-sends the same body', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(`${API}/api/farmers`, async ({ request }) => {
        bodies.push(await request.json());
        if (bodies.length === 1) {
          return HttpResponse.json({ detail: 'upstream exploded' }, { status: 500 });
        }
        return HttpResponse.json(farmerResponse, { status: 201 });
      }),
    );
    mockNetwork();

    const { router } = renderCase('/case/new');
    const user = await fillFarmerForm();
    await user.click(screen.getByRole('button', { name: /create farmer/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('upstream exploded');

    await user.click(within(alert).getByRole('button', { name: /retry/i }));

    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1]).toEqual(bodies[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/case/farmer-1'));
  });
});
