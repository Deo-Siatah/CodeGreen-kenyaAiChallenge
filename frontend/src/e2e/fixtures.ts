import { request, type APIRequestContext } from '@playwright/test';
import { z } from 'zod';

export const API_URL = process.env.E2E_API_URL ?? 'http://127.0.0.1:8001';

const farmerSchema = z.object({
  id: z.string(),
  full_name: z.string(),
});

const entitySchema = z.object({
  id: z.string(),
});

const startSchema = z.object({
  session_id: z.string(),
});

const statusSchema = z.object({
  participants: z.array(
    z.object({
      id: z.string(),
      participant_type: z.string(),
    }),
  ),
});

export interface ScoredFarmer {
  id: string;
  fullName: string;
}

export async function newApi(): Promise<APIRequestContext> {
  return request.newContext({ baseURL: API_URL, timeout: 90_000 });
}

async function post(
  api: APIRequestContext,
  path: string,
  data: unknown,
): Promise<unknown> {
  const response = await api.post(path, { data });
  if (!response.ok()) {
    throw new Error(
      `POST ${path} failed with ${response.status()}: ${await response.text()}`,
    );
  }
  return response.json();
}

export async function createScoredFarmer(
  api: APIRequestContext,
  prefix: string,
): Promise<ScoredFarmer> {
  const stamp = `${Date.now()}${Math.floor(Math.random() * 10_000)}`;
  const suffix = stamp.slice(-10);
  const run = `${stamp.slice(-6)}${Math.random().toString(36).slice(2, 6)}`;

  const farmer = farmerSchema.parse(
    await post(api, '/api/farmers', {
      full_name: `${prefix} ${run}`,
      national_id: `E2E-${stamp}`,
      phone: `+2547${suffix}`,
      gender: 'female',
      date_of_birth: '1985-04-12',
      location: 'Kiambu',
      village: 'E2E Village',
      sub_county: 'Kiambu',
      county: 'Kiambu',
      farming_type: 'mixed',
      years_farming: 6,
    }),
  );

  await post(api, `/api/farmers/${farmer.id}/farm`, {
    acreage: 1.5,
    production_type: 'crop',
    latitude: -1.1714,
    longitude: 36.8356,
  });

  const trustSource = entitySchema.parse(
    await post(api, '/api/trust/sources', {
      name: `E2E Chief ${run}`,
      category: 'Chief',
      phone: `+2548${suffix}`,
      national_id: `E2E-TS-${stamp}`,
      location: 'Kiambu',
    }),
  );
  const marketActor = entitySchema.parse(
    await post(api, '/api/trust/market-actors', {
      name: `E2E Buyer ${run}`,
      actor_type: 'Buyer',
      phone: `+2549${suffix}`,
      location: 'Kiambu',
    }),
  );
  const socialGroup = entitySchema.parse(
    await post(api, '/api/trust/social-groups', {
      name: `E2E Chama ${run}`,
      group_type: 'Chama',
      location: 'Kiambu',
      formation_year: 2019,
    }),
  );

  await post(api, `/api/farmers/${farmer.id}/link-trust-source`, {
    related_id: trustSource.id,
  });
  await post(api, `/api/farmers/${farmer.id}/link-market-actor`, {
    related_id: marketActor.id,
  });
  await post(api, `/api/farmers/${farmer.id}/link-social-group`, {
    related_id: socialGroup.id,
  });

  const started = startSchema.parse(
    await post(api, '/api/verify/start', { farmer_id: farmer.id }),
  );
  const statusResponse = await api.get(
    `/api/verify/${started.session_id}/status`,
  );
  if (!statusResponse.ok()) {
    throw new Error(
      `GET verification status failed with ${statusResponse.status()}: ${await statusResponse.text()}`,
    );
  }
  const status = statusSchema.parse(await statusResponse.json());

  const ids = new Map(
    status.participants.map((participant) => [
      participant.participant_type,
      participant.id,
    ]),
  );
  const trustSourceParticipant = ids.get('trust_source');
  const marketActorParticipant = ids.get('market_actor');
  const socialGroupParticipant = ids.get('social_group');

  if (
    !trustSourceParticipant ||
    !marketActorParticipant ||
    !socialGroupParticipant
  ) {
    throw new Error('Verification session did not create all three participants');
  }

  await post(
    api,
    `/api/verify/${started.session_id}/respond/${trustSourceParticipant}`,
    {
      participant_type: 'trust_source',
      rating: 4,
      comments: 'Known in the community for years.',
      personal_knowledge_flag: true,
    },
  );
  await post(
    api,
    `/api/verify/${started.session_id}/respond/${marketActorParticipant}`,
    {
      participant_type: 'market_actor',
      reliability_rating: 4,
      purchase_frequency: 'weekly',
      relationship_months: 24,
      avg_volume_kg: 40,
    },
  );
  await post(
    api,
    `/api/verify/${started.session_id}/respond/${socialGroupParticipant}`,
    {
      participant_type: 'social_group',
      consecutive_cycles: 5,
      last_contribution_date: '2026-09-01',
      contribution_amount: 500,
    },
  );

  return { id: farmer.id, fullName: farmer.full_name };
}
