import { describe, expect, it } from 'vitest';
import { ringTarget } from './ring';
import type { NodeKind } from './types';

const RING_KINDS: NodeKind[] = [
  'farm',
  'trust_source',
  'market_actor',
  'social_group',
  'loan',
];

function distance(a: { x: number; y: number }, b: { x: number; y: number }): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

describe('ringTarget', () => {
  it('places the farmer at the origin', () => {
    expect(ringTarget('farmer', 0, 1)).toEqual({ x: 0, y: 0 });
    expect(ringTarget('farmer', 3, 12)).toEqual({ x: 0, y: 0 });
  });

  it('is deterministic for identical input', () => {
    expect(ringTarget('trust_source', 4, 9)).toEqual(ringTarget('trust_source', 4, 9));
  });

  it('keeps at least 56px between every pair on a ring for up to 12 nodes', () => {
    for (const kind of RING_KINDS) {
      for (let count = 2; count <= 12; count += 1) {
        const points = Array.from({ length: count }, (_, index) => ringTarget(kind, index, count));
        for (let i = 0; i < points.length; i += 1) {
          for (let j = i + 1; j < points.length; j += 1) {
            const a = points[i];
            const b = points[j];
            if (!a || !b) {
              throw new Error('missing point');
            }
            expect(distance(a, b)).toBeGreaterThanOrEqual(56);
          }
        }
      }
    }
  });

  it('gives the ring-2 kinds distinct angular sectors', () => {
    const trust = ringTarget('trust_source', 0, 1);
    const market = ringTarget('market_actor', 0, 1);
    const social = ringTarget('social_group', 0, 1);

    expect(trust).not.toEqual(market);
    expect(market).not.toEqual(social);
    expect(trust).not.toEqual(social);
  });
});
