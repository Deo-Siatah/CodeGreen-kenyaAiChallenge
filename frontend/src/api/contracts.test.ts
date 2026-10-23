import { afterEach, describe, expect, it } from 'vitest';
import { AxiosHeaders, type AxiosAdapter } from 'axios';
import { client } from './client';
import { ApiError } from './errors';
import {
  createMarketActor,
  createSocialGroup,
  createTrustSource,
  linkTrustSource,
} from './endpoints/trust';
import { getFarmerNetwork } from './endpoints/farmers';
import {
  getVerificationBreakdown,
  startVerification,
  submitTrustSourceResponse,
} from './endpoints/verification';

const originalAdapter = client.defaults.adapter;

function respondWith(data: unknown): void {
  const adapter: AxiosAdapter = async (config) => ({
    data,
    status: 200,
    statusText: 'OK',
    headers: new AxiosHeaders(),
    config,
  });
  client.defaults.adapter = adapter;
}

afterEach(() => {
  client.defaults.adapter = originalAdapter;
});

const timestamp = '2026-10-19T10:00:00Z';

describe('trust response contracts', () => {
  it('accepts a trust source create response', async () => {
    respondWith({
      id: '2f1c4a4e-0000-4000-8000-000000000001',
      full_name: 'Chief Wanjiku',
      category: 'Chief',
      phone: '+254700000001',
      national_id: null,
      location: 'Nairobi',
      institution_id: null,
      created_at: timestamp,
      updated_at: timestamp,
    });

    const result = await createTrustSource({
      name: 'Chief Wanjiku',
      category: 'Chief',
      phone: '+254700000001',
      national_id: null,
      location: 'Nairobi',
    });

    expect(result.full_name).toBe('Chief Wanjiku');
  });

  it('accepts a market actor create response', async () => {
    respondWith({
      id: '2f1c4a4e-0000-4000-8000-000000000002',
      name: 'Nairobi Aggregators',
      actor_type: 'Aggregator',
      phone: null,
      location: null,
      created_at: timestamp,
      updated_at: timestamp,
    });

    const result = await createMarketActor({
      name: 'Nairobi Aggregators',
      actor_type: 'Aggregator',
      phone: null,
      location: 'Nairobi',
    });

    expect(result.actor_type).toBe('Aggregator');
  });

  it('accepts a social group create response', async () => {
    respondWith({
      id: '2f1c4a4e-0000-4000-8000-000000000003',
      name: 'Mwangaza Chama',
      group_type: null,
      location: null,
      formation_year: null,
      created_at: timestamp,
      updated_at: timestamp,
    });

    const result = await createSocialGroup({
      name: 'Mwangaza Chama',
      group_type: 'Savings',
      location: 'Kiambu',
      formation_year: null,
    });

    expect(result.name).toBe('Mwangaza Chama');
  });

  it('accepts a link response with relation columns', async () => {
    respondWith({
      farmer_id: '2f1c4a4e-0000-4000-8000-000000000010',
      trust_source_id: '2f1c4a4e-0000-4000-8000-000000000001',
      relationship_type: null,
      years_known: null,
      created_at: timestamp,
      updated_at: timestamp,
    });

    const result = await linkTrustSource('2f1c4a4e-0000-4000-8000-000000000010', {
      related_id: '2f1c4a4e-0000-4000-8000-000000000001',
    });

    expect(result.farmer_id).toBe('2f1c4a4e-0000-4000-8000-000000000010');
  });

  it('maps a malformed trust response to a contract error', async () => {
    respondWith({ id: 'missing-everything-else' });

    await expect(
      createTrustSource({
        name: 'Chief Wanjiku',
        category: 'Chief',
        phone: null,
        national_id: null,
        location: 'Nairobi',
      }),
    ).rejects.toBeInstanceOf(ApiError);
  });
});

describe('farmer network contract', () => {
  it('accepts nullable farm, score and loan fields', async () => {
    respondWith({
      farmer: {
        id: '2f1c4a4e-0000-4000-8000-000000000010',
        full_name: 'Jane Wanjiru',
        county: 'Kiambu',
      },
      farms: [
        {
          id: '2f1c4a4e-0000-4000-8000-000000000020',
          acreage: null,
          latitude: null,
          longitude: null,
        },
      ],
      trust_sources: [
        {
          id: '2f1c4a4e-0000-4000-8000-000000000001',
          name: 'Chief Wanjiku',
          category: 'Chief',
          phone_masked: null,
          credibility_score: 1,
        },
      ],
      market_actors: [],
      social_groups: [],
      latest_session: null,
      current_score: {
        id: '2f1c4a4e-0000-4000-8000-000000000030',
        character_score: null,
        capacity_score: null,
        final_score: null,
        decision: null,
        recommended_amount: null,
      },
      loans: [
        {
          id: '2f1c4a4e-0000-4000-8000-000000000040',
          amount: null,
          status: 'pending',
          applied_at: null,
        },
      ],
    });

    const result = await getFarmerNetwork('2f1c4a4e-0000-4000-8000-000000000010');

    expect(result.farms[0]?.acreage).toBeNull();
    expect(result.current_score?.final_score).toBeNull();
  });
});

describe('verification contracts', () => {
  it('accepts a start response', async () => {
    respondWith({
      session_id: '2f1c4a4e-0000-4000-8000-000000000050',
      farmer_id: '2f1c4a4e-0000-4000-8000-000000000010',
      status: 'pending',
    });

    const result = await startVerification({
      farmer_id: '2f1c4a4e-0000-4000-8000-000000000010',
    });

    expect(result.status).toBe('pending');
  });

  it('accepts a submit response', async () => {
    respondWith({
      participant_status: 'responded',
      session_status: 'in_progress',
      score_result: null,
    });

    const result = await submitTrustSourceResponse(
      '2f1c4a4e-0000-4000-8000-000000000050',
      '2f1c4a4e-0000-4000-8000-000000000060',
      {
        participant_type: 'trust_source',
        rating: 4,
        comments: null,
        personal_knowledge_flag: true,
      },
    );

    expect(result.session_status).toBe('in_progress');
  });

  it('accepts a breakdown whose raw_value is a string', async () => {
    respondWith({
      profile: {
        id: '2f1c4a4e-0000-4000-8000-000000000030',
        final_score: 68,
      },
      axis_note: 'combined',
      components: [
        {
          axis: 'character',
          component_name: 'discipline_proxy',
          raw_value: '5 consecutive Chama cycles',
          contribution: 24,
          weight: 0.35,
          pool_id: null,
          trust_source_id: null,
          market_actor_id: null,
        },
      ],
    });

    const result = await getVerificationBreakdown(
      '2f1c4a4e-0000-4000-8000-000000000050',
    );

    expect(result.components[0]?.raw_value).toBe('5 consecutive Chama cycles');
  });
});
