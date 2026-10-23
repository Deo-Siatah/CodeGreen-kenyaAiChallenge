import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph } from '@/test/case-harness';
import {
  API,
  linkResponse,
  trustSourceEntity,
} from '@/test/workflow-fixtures';
import { useGraphStore } from '@/features/graph/store';

const networkBody = {
  farmer: { id: 'farmer-1', full_name: 'Ann Wanjiku', county: 'Nakuru' },
  farms: [{ id: 'farm-1', acreage: 2.5, latitude: -0.3, longitude: 36.1 }],
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

async function openNetworkStep() {
  const { container } = renderCase('/case/farmer-1');
  await screen.findByRole('button', { name: /add community/i });
  return container;
}

async function fillCommunity() {
  const user = userEvent.setup({ delay: null });
  await user.type(screen.getByLabelText(/community member name/i), 'Kariuki');
  await user.type(screen.getByLabelText(/community member phone/i), '0711111111');
  await user.type(screen.getByLabelText(/community member location/i), 'Nakuru');
  await user.selectOptions(screen.getByLabelText(/category/i), 'administrative official');
  return user;
}

afterEach(() => {
  resetGraph();
});

describe('Step 3 — Network', () => {
  it('6. adding a verifier issues create then link and leaves a live node with one edge', async () => {
    const calls: string[] = [];
    server.use(
      http.post(`${API}/api/trust/sources`, async ({ request }) => {
        calls.push('create');
        const body = (await request.json()) as { name: string };
        expect(body.name).toBe('Kariuki');
        return HttpResponse.json(trustSourceEntity, { status: 201 });
      }),
      http.post(`${API}/api/farmers/farmer-1/link-trust-source`, async () => {
        calls.push('link');
        return HttpResponse.json(linkResponse('farmer-1', 'trust_source_id', 'ts-1'), {
          status: 201,
        });
      }),
    );
    mockNetwork();
    await openNetworkStep();

    const edgesBefore = Object.keys(useGraphStore.getState().edges).length;
    const user = await fillCommunity();
    await user.click(screen.getByRole('button', { name: /add community/i }));

    await waitFor(() => expect(useGraphStore.getState().nodes['ts-1']).toBeDefined());
    expect(calls).toEqual(['create', 'link']);

    const state = useGraphStore.getState();
    expect(state.nodes['ts-1']?.state).toBe('live');
    expect(Object.keys(state.edges).length).toBe(edgesBefore + 1);
    expect(
      Object.values(state.edges).some(
        (edge) => edge.from === 'ts-1' || edge.to === 'ts-1',
      ),
    ).toBe(true);
  });

  it('7. a failed link leaves no ghost node and shows the error', async () => {
    server.use(
      http.post(`${API}/api/trust/sources`, () =>
        HttpResponse.json(trustSourceEntity, { status: 201 }),
      ),
      http.post(`${API}/api/farmers/farmer-1/link-trust-source`, () =>
        HttpResponse.json({ detail: 'link exploded' }, { status: 500 }),
      ),
    );
    mockNetwork();
    await openNetworkStep();

    const user = await fillCommunity();
    await user.click(screen.getByRole('button', { name: /add community/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('link exploded');
    expect(useGraphStore.getState().nodes['ts-1']).toBeUndefined();
  });

  it('10. graph labels never contain a full phone number', async () => {
    server.use(
      http.post(`${API}/api/trust/sources`, () =>
        HttpResponse.json(trustSourceEntity, { status: 201 }),
      ),
      http.post(`${API}/api/farmers/farmer-1/link-trust-source`, () =>
        HttpResponse.json(linkResponse('farmer-1', 'trust_source_id', 'ts-1'), { status: 201 }),
      ),
    );
    mockNetwork();
    const container = await openNetworkStep();

    const user = await fillCommunity();
    await user.click(screen.getByRole('button', { name: /add community/i }));

    await waitFor(() => expect(useGraphStore.getState().nodes['ts-1']).toBeDefined());

    expect(container.textContent ?? '').not.toContain('0711111111');
    expect(container.textContent ?? '').not.toMatch(/\b0\d{9}\b/);
    expect(useGraphStore.getState().nodes['ts-1']?.label).toBe('Kariuki');
  });
});
