import { describe, expect, it } from 'vitest';
import { fitBounds } from './fitBounds';

function aspectOf(box: { width: number; height: number }): number {
  return box.width / box.height;
}

describe('fitBounds', () => {
  it('respects padding on the tight axes', () => {
    const box = fitBounds(
      [
        { x: 0, y: 0 },
        { x: 100, y: 200 },
      ],
      0.5,
      10,
    );

    expect(box.width).toBeGreaterThanOrEqual(120);
    expect(box.height).toBeGreaterThanOrEqual(220);
  });

  it('returns a sane default box for a single point', () => {
    const box = fitBounds([{ x: 10, y: 20 }], 1, 0);

    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);
    expect(box.width).toBeGreaterThanOrEqual(400);
    expect(box.x).toBeLessThan(10);
    expect(box.x + box.width).toBeGreaterThan(10);
    expect(box.y).toBeLessThan(20);
    expect(box.y + box.height).toBeGreaterThan(20);
  });

  it('preserves the requested aspect ratio', () => {
    const inputs: Array<{ points: Array<{ x: number; y: number }>; aspect: number }> = [
      { points: [{ x: 0, y: 0 }], aspect: 16 / 9 },
      { points: [{ x: -50, y: 0 }, { x: 50, y: 10 }], aspect: 0.5 },
      { points: [{ x: 0, y: 0 }, { x: 0, y: 500 }], aspect: 2 },
    ];

    for (const input of inputs) {
      const box = fitBounds(input.points, input.aspect, 8);
      expect(aspectOf(box)).toBeCloseTo(input.aspect, 5);
    }
  });

  it('handles an empty point list with a centred default box', () => {
    const box = fitBounds([], 1, 0);

    expect(box.width).toBeGreaterThan(0);
    expect(box.height).toBeGreaterThan(0);
    expect(aspectOf(box)).toBeCloseTo(1, 5);
    expect(box.x + box.width / 2).toBeCloseTo(0, 5);
    expect(box.y + box.height / 2).toBeCloseTo(0, 5);
  });
});
