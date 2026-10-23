import { client } from '../client';
import { schemas, type StatsOverviewResponse } from '../schemas';
import { validate } from '../validate';

export async function getStatsOverview(
  signal?: AbortSignal,
): Promise<StatsOverviewResponse> {
  const response = await client.get('/api/stats/overview', { signal });
  return validate(schemas.StatsOverviewResponse, response.data);
}
