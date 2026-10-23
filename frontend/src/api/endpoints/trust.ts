import { client } from '../client';
import {
  schemas,
  type LinkRequest,
  type MarketActorCreate,
  type SocialGroupCreate,
  type TrustSourceCreate,
} from '../schemas';
import { validate } from '../validate';

export async function createTrustSource(data: TrustSourceCreate, signal?: AbortSignal) {
  const response = await client.post('/api/trust/sources', data, { signal });
  return validate(schemas.TrustSourceEntity, response.data);
}

export async function createMarketActor(data: MarketActorCreate, signal?: AbortSignal) {
  const response = await client.post('/api/trust/market-actors', data, { signal });
  return validate(schemas.MarketActorEntity, response.data);
}

export async function createSocialGroup(data: SocialGroupCreate, signal?: AbortSignal) {
  const response = await client.post('/api/trust/social-groups', data, { signal });
  return validate(schemas.SocialGroupEntity, response.data);
}

export async function linkTrustSource(
  farmerId: string,
  data: LinkRequest,
  signal?: AbortSignal,
) {
  const response = await client.post(`/api/farmers/${farmerId}/link-trust-source`, data, { signal });
  return validate(schemas.EntityLinkResponse, response.data);
}

export async function linkMarketActor(
  farmerId: string,
  data: LinkRequest,
  signal?: AbortSignal,
) {
  const response = await client.post(`/api/farmers/${farmerId}/link-market-actor`, data, { signal });
  return validate(schemas.EntityLinkResponse, response.data);
}

export async function linkSocialGroup(
  farmerId: string,
  data: LinkRequest,
  signal?: AbortSignal,
) {
  const response = await client.post(`/api/farmers/${farmerId}/link-social-group`, data, { signal });
  return validate(schemas.EntityLinkResponse, response.data);
}
