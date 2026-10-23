import { http, HttpResponse } from 'msw';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { server } from '@/test/server';
import { renderCase, resetGraph } from '@/test/case-harness';
import { API } from '@/test/workflow-fixtures';
import { useGraphStore } from '@/features/graph/store';

const scoreProfile = {
  id: 'sp-1',
  farmer_id: 'farmer-1',
  version: 2,
  character_score: 71.25,
  capacity_score: null,
  final_score: 68,
  decision: 'REVIEW_REQUIRED',
  recommended_amount: 15000,
  computed_at: '2026-10-19T09:00:00Z',
  is_current: true,
};

const networkBody = {
  farmer: { id: 'farmer-1', full_name: 'Ann Wanjiku', county: 'Nakuru' },
  farms: [{ id: 'farm-1', acreage: 2.5, latitude: -0.3, longitude: 36.1 }],
  trust_sources: [
    {
      id: 'ts-1',
      name: 'Kariuki',
      category: 'administrative official',
      phone_masked: null,
      credibility_score: 1,
    },
  ],
  market_actors: [],
  social_groups: [],
  latest_session: {
    id: 'sess-9',
    status: 'completed',
    participants: [
      {
        id: 'p-9',
        participant_type: 'trust_source',
        participant_id: 'ts-1',
        responded: '2026-10-19T08:30:00Z',
      },
    ],
  },
  current_score: null,
  loans: [],
};

async function openScore() {
  server.use(
    http.get(`${API}/api/farmers/farmer-1/network`, () => HttpResponse.json(networkBody)),
    http.get(`${API}/api/verify/sess-9/result`, () =>
      HttpResponse.json({ session_id: 'sess-9', score_profile: scoreProfile }),
    ),
    http.get(`${API}/api/verify/sess-9/breakdown`, () =>
      HttpResponse.json({
        profile: scoreProfile,
        axis_note: 'capacity axis unavailable - character only',
        components: [
          {
            axis: 'character',
            component_name: 'community_testimony',
            raw_value: 'rating=4 (1 source)',
            contribution: 71.25,
            weight: 0.6,
            pool_id: 'pool-1',
            trust_source_id: 'ts-1',
            market_actor_id: null,
          },
        ],
      }),
    ),
  );

  renderCase('/case/farmer-1');
  const user = userEvent.setup({ delay: null });
  const step = await screen.findByRole('button', { name: /^5 score$/i });
  await user.click(step);
  return user;
}

afterEach(() => {
  resetGraph();
});

describe('Step 5 — Score', () => {
  it('shows the two axes, the components, and the character-only note', async () => {
    await openScore();

    expect(await screen.findByTestId('score-final')).toHaveTextContent('68.0');
    expect(screen.getByTestId('score-character')).toHaveTextContent('71.3');
    expect(screen.getByTestId('score-capacity')).toHaveTextContent('No satellite reading');
    expect(screen.getByTestId('score-amount')).toHaveTextContent('15,000');
    expect(screen.getByText('Review required')).toBeInTheDocument();

    expect(screen.getByTestId('breakdown')).toHaveTextContent('character only');
    expect(screen.getByTestId('breakdown-row')).toHaveTextContent('community testimony');
    expect(screen.getByTestId('breakdown-row')).toHaveTextContent('rating=4 (1 source)');

    expect(useGraphStore.getState().score).toEqual({
      final: 68,
      character: 71.25,
      capacity: null,
      decision: 'REVIEW_REQUIRED',
      recommendedAmount: 15000,
    });
  });

  it('generates an explanation for the chosen audience and language', async () => {
    let requested: { mode: string | null; language: string | null } | null = null;
    server.use(
      http.get(`${API}/api/verify/sess-9/explanation`, ({ request }) => {
        const url = new URL(request.url);
        requested = {
          mode: url.searchParams.get('mode'),
          language: url.searchParams.get('language'),
        };
        return HttpResponse.json({
          session_id: 'sess-9',
          explanation: '**Strong** community evidence on the character axis.',
        });
      }),
    );

    const user = await openScore();
    await screen.findByTestId('score-final');

    await user.selectOptions(screen.getByLabelText(/audience/i), 'expert');
    await user.selectOptions(screen.getByLabelText(/language/i), 'Swahili');
    await user.click(screen.getByRole('button', { name: /generate explanation/i }));

    expect(await screen.findByTestId('explanation-text')).toHaveTextContent(
      'Strong community evidence on the character axis.',
    );
    expect(requested).toEqual({ mode: 'expert', language: 'Swahili' });
  });
});
