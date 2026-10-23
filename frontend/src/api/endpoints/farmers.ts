import { client } from '../client';
import {
  schemas,
  type FarmResponse,
  type FarmRouteCreate,
  type FarmerDetailResponse,
  type FarmerRouteCreate,
} from '../schemas';
import { validate } from '../validate';

export async function createFarm(
  farmerId: string,
  data: FarmRouteCreate,
  signal?: AbortSignal,
): Promise<FarmResponse> {
  const response = await client.post(`/api/farmers/${farmerId}/farm`, data, { signal });
  return validate(schemas.FarmResponse, response.data);
}

export async function createFarmer(
  data: FarmerRouteCreate,
  signal?: AbortSignal,
): Promise<FarmerDetailResponse> {
  const response = await client.post('/api/farmers', data, { signal });
  return validate(schemas.FarmerDetailResponse, response.data);
}

export async function getFarmer(
  id: string,
  signal?: AbortSignal,
): Promise<FarmerDetailResponse> {
  const response = await client.get(`/api/farmers/${id}`, { signal });
  return validate(schemas.FarmerDetailResponse, response.data);
}

export async function listFarmers(
  params?: {
    limit?: number;
    offset?: number;
  },
  signal?: AbortSignal,
): Promise<ReturnType<typeof schemas.FarmersListResponse.parse>> {
  const response = await client.get('/api/farmers', { params, signal });
  return validate(schemas.FarmersListResponse, response.data);
}

export async function getFarmerNetwork(
  farmerId: string,
  signal?: AbortSignal,
): Promise<ReturnType<typeof schemas.NetworkResponse.parse>> {
  const response = await client.get(`/api/farmers/${farmerId}/network`, { signal });
  return validate(schemas.NetworkResponse, response.data);
}
