import { http, HttpResponse } from 'msw';
import { act, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph, seedGraph } from '@/test/case-harness';
import { API } from '@/test/workflow-fixtures';
import { liveFlowEvents, networkPayload } from '@/test/graph-fixture';
import { graphReducer, initialState, type GraphEvent } from '@/domain/graph';
import { useGraphStore } from '@/features/graph/store';

function mockNetwork() {
  server.use(
    http.get(`${API}/api/farmers/farmer-1/network`, () => HttpResponse.json(networkPayload)),
  );
}

afterEach(() => {
  resetGraph();
});

describe('CaseLayout — stepper locks', () => {
  it('1. locks step 2 until a farmer exists and step 4 until a community verifier is linked', () => {
    resetGraph();
    renderCase('/case/new');

    const step = (n: number, label: string) =>
      screen.getByRole('button', { name: new RegExp(`^${n} ${label}`, 'i') });

    expect(step(2, 'Farm')).toBeDisabled();
    expect(step(4, 'Verify')).toBeDisabled();

    act(() => {
      seedGraph([
        { type: 'FARMER_CREATED', farmerId: 'farmer-1', label: 'Ann' },
        { type: 'FARM_CREATED', farmId: 'farm-1', farmerId: 'farmer-1' },
      ]);
    });

    expect(step(2, 'Farm')).toBeEnabled();
    expect(step(3, 'Network')).toBeEnabled();
    expect(step(4, 'Verify')).toBeDisabled();

    act(() => {
      seedGraph([
        { type: 'FARMER_CREATED', farmerId: 'farmer-1', label: 'Ann' },
        { type: 'FARM_CREATED', farmId: 'farm-1', farmerId: 'farmer-1' },
        { type: 'VERIFIER_ADDED', verifierId: 'ts-1', kind: 'trust_source', label: 'Kariuki' },
        { type: 'VERIFIER_LINKED', farmerId: 'farmer-1', verifierId: 'ts-1', kind: 'trust_source' },
      ]);
    });

    expect(step(4, 'Verify')).toBeEnabled();
  });
});

describe('CaseLayout — hydration', () => {
  it('8. rebuilding from the network fixture yields the same node and edge ids as the live flow', async () => {
    mockNetwork();
    renderCase('/case/farmer-1');

    const expected = liveFlowEvents.reduce<ReturnType<typeof graphReducer>>(
      (state, event: GraphEvent) => graphReducer(state, event),
      initialState,
    );

    await waitFor(() =>
      expect(Object.keys(useGraphStore.getState().nodes)).toHaveLength(
        Object.keys(expected.nodes).length,
      ),
    );

    expect(Object.keys(useGraphStore.getState().nodes).sort()).toEqual(
      Object.keys(expected.nodes).sort(),
    );
    expect(Object.keys(useGraphStore.getState().edges).sort()).toEqual(
      Object.keys(expected.edges).sort(),
    );
  });

  it('shows a not-found state for an unknown farmer', async () => {
    server.use(
      http.get(`${API}/api/farmers/missing/network`, () =>
        HttpResponse.json({ detail: 'Farmer not found' }, { status: 404 }),
      ),
    );

    renderCase('/case/missing');

    expect(await screen.findByText(/farmer not found/i)).toBeInTheDocument();
  });

  it('9. the evidence ledger shows one line per API call with its status', async () => {
    mockNetwork();
    renderCase('/case/farmer-1');

    const ledger = await screen.findByTestId('ledger');

    await waitFor(() =>
      expect(ledger.querySelectorAll('[data-testid="ledger-entry"]').length).toBeGreaterThan(0),
    );

    const text = ledger.textContent ?? '';
    expect(text).toContain('GET');
    expect(text).toContain('/api/farmers/farmer-1/network');
    expect(text).toContain('200');
  });
});
