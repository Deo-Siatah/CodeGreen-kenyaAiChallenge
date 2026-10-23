import { describe, expect, it } from 'vitest';
import { replayRoute } from './routes';

describe('replayRoute', () => {
  it('is available in every environment and points at /replay', () => {
    const routes = replayRoute();

    expect(routes).toHaveLength(1);
    expect(routes[0]?.path).toBe('/replay');
  });
});
