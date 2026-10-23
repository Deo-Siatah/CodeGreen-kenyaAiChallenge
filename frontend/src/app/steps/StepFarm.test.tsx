import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph } from '@/test/case-harness';
import { API, farmRequestBody, farmResponse } from '@/test/workflow-fixtures';
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

afterEach(() => {
  resetGraph();
});

describe('Step 2 — Farm', () => {
  it('fills coordinates from a quick-pick preset', async () => {
    mockNetwork();
    renderCase('/case/farmer-1');

    const user = userEvent.setup({ delay: null });
    await user.click(await screen.findByRole('button', { name: /use nakuru/i }));

    expect(screen.getByLabelText(/latitude/i)).toHaveValue(String(farmRequestBody.latitude));
    expect(screen.getByLabelText(/longitude/i)).toHaveValue(String(farmRequestBody.longitude));
  });

  it('rejects an out-of-range latitude inline', async () => {
    mockNetwork();
    renderCase('/case/farmer-1');

    const user = userEvent.setup({ delay: null });
    await user.click(await screen.findByRole('button', { name: /use nakuru/i }));
    const latitude = screen.getByLabelText(/latitude/i);
    await user.clear(latitude);
    await user.type(latitude, '200');
    await user.selectOptions(screen.getByLabelText(/production type/i), 'Crop');
    await user.type(screen.getByLabelText(/acreage/i), '2.5');
    await user.click(screen.getByRole('button', { name: /create farm/i }));

    expect(await screen.findByText(/latitude must be between -90 and 90/i)).toBeInTheDocument();
  });

  it('posts the farm and dispatches FARM_CREATED', async () => {
    let captured: unknown = null;
    server.use(
      http.post(`${API}/api/farmers/farmer-1/farm`, async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json(farmResponse, { status: 201 });
      }),
    );
    mockNetwork();
    renderCase('/case/farmer-1');

    const user = userEvent.setup({ delay: null });
    await user.click(await screen.findByRole('button', { name: /use nakuru/i }));
    await user.type(screen.getByLabelText(/acreage/i), '2.5');
    await user.selectOptions(screen.getByLabelText(/production type/i), 'Crop');
    await user.click(screen.getByRole('button', { name: /create farm/i }));

    await waitFor(() => expect(useGraphStore.getState().nodes['farm-1']).toBeDefined());
    expect(captured).toEqual(farmRequestBody);
  });
});
