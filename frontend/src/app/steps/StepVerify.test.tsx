import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph } from '@/test/case-harness';
import { API } from '@/test/workflow-fixtures';
import { useGraphStore } from '@/features/graph/store';
import { useCaseStore } from '../caseStore';

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
  current_score: null,
  loans: [],
};

const participant = {
  id: 'p-1',
  session_id: 'sess-1',
  participant_type: 'trust_source',
  participant_id: 'ts-1',
  contacted_at: '2026-10-19T08:00:00Z',
  responded_at: null,
  response: null,
  created_at: '2026-10-19T08:00:00Z',
  updated_at: '2026-10-19T08:00:00Z',
};

const scoreProfile = {
  id: 'sp-1',
  farmer_id: 'farmer-1',
  version: 1,
  character_score: 71.25,
  capacity_score: 63,
  final_score: 68,
  decision: 'ELIGIBLE',
  recommended_amount: 15000,
  computed_at: '2026-10-19T09:00:00Z',
  is_current: true,
};

function mockStartAndStatus() {
  server.use(
    http.get(`${API}/api/farmers/farmer-1/network`, () => HttpResponse.json(networkBody)),
    http.post(`${API}/api/verify/start`, () => {
      return HttpResponse.json(
        { session_id: 'sess-1', farmer_id: 'farmer-1', status: 'pending' },
        { status: 201 },
      );
    }),
    http.get(`${API}/api/verify/sess-1/status`, () =>
      HttpResponse.json({ session_id: 'sess-1', status: 'pending', participants: [participant] }),
    ),
  );
}

async function startRound() {
  renderCase('/case/farmer-1');
  const user = userEvent.setup({ delay: null });
  await user.click(await screen.findByRole('button', { name: /start verification round/i }));
  await screen.findByText(/round pending/i);
  return user;
}

afterEach(() => {
  resetGraph();
});

describe('Step 4 — Verify', () => {
  it('starts a round, keys a community answer, and lands on the score', async () => {
    let submitted: unknown = null;
    server.use(
      http.post(`${API}/api/verify/sess-1/respond/p-1`, async ({ request }) => {
        submitted = await request.json();
        return HttpResponse.json({
          participant_status: 'rating=4',
          session_status: 'completed',
          score_result: scoreProfile,
        });
      }),
      http.get(`${API}/api/verify/sess-1/result`, () =>
        HttpResponse.json({ session_id: 'sess-1', score_profile: scoreProfile }),
      ),
      http.get(`${API}/api/verify/sess-1/breakdown`, () =>
        HttpResponse.json({
          profile: scoreProfile,
          axis_note: 'combined',
          components: [
            {
              axis: 'character',
              component_name: 'community_testimony',
              raw_value: '4',
              contribution: 71.25,
              weight: 0.6,
              pool_id: null,
              trust_source_id: 'ts-1',
              market_actor_id: null,
            },
          ],
        }),
      ),
    );
    mockStartAndStatus();

    const user = await startRound();

    await waitFor(() =>
      expect(useGraphStore.getState().nodes['ts-1']?.state).toBe('pending'),
    );
    await user.click(screen.getByRole('button', { name: /call kariuki/i }));

    expect(screen.getByTestId('ussd-prompt')).toHaveTextContent('Do you personally know Kariuki?');
    await user.click(screen.getByRole('button', { name: /^1 yes$/i }));
    await user.click(screen.getByRole('button', { name: /^4 excellent$/i }));
    await user.click(screen.getByRole('button', { name: /no, that is all/i }));
    await user.click(screen.getByRole('button', { name: /send response/i }));

    await waitFor(() => expect(useGraphStore.getState().nodes['ts-1']?.state).toBe('responded'));
    expect(submitted).toEqual({
      participant_type: 'trust_source',
      rating: 4,
      comments: null,
      personal_knowledge_flag: true,
    });
    expect(useGraphStore.getState().nodes['ts-1']?.rating).toBe(4);

    await user.click(await screen.findByRole('button', { name: /continue to score/i }));

    expect(useCaseStore.getState().step).toBe(5);
    expect(await screen.findByTestId('score-final')).toHaveTextContent('68.0');
    expect(screen.getByTestId('score-character')).toHaveTextContent('71.3');
    expect(screen.getByTestId('breakdown-row')).toHaveTextContent('community testimony');
  });

  it('records a missed call without opening the handset', async () => {
    let timedOut: string | null = null;
    server.use(
      http.post(`${API}/api/verify/sess-1/timeout/p-1`, () => {
        timedOut = 'p-1';
        return HttpResponse.json({
          participant_status: 'timeout',
          session_status: 'in_progress',
          score_result: null,
        });
      }),
    );
    mockStartAndStatus();

    const user = await startRound();
    await waitFor(() =>
      expect(useGraphStore.getState().nodes['ts-1']?.state).toBe('pending'),
    );

    await user.click(screen.getByRole('button', { name: /no answer/i }));

    await waitFor(() =>
      expect(useGraphStore.getState().nodes['ts-1']?.state).toBe('timed_out'),
    );
    expect(timedOut).toBe('p-1');
    expect(screen.queryByTestId('ussd-prompt')).not.toBeInTheDocument();
  });
});
