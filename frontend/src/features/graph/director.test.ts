import { afterEach, describe, expect, it, vi } from 'vitest';
import { beatDuration, createDirector } from './director';
import type { GraphEvent } from '@/domain/graph';

const e1: GraphEvent = { type: 'FARMER_CREATED', farmerId: 'f1', label: 'Ann' };
const e2: GraphEvent = { type: 'FARM_CREATED', farmId: 'farm1', farmerId: 'f1' };
const e3: GraphEvent = { type: 'VERIFIER_ADDED', verifierId: 'v1', kind: 'trust_source', label: 'Chief' };

afterEach(() => {
  vi.useRealTimers();
});

describe('createDirector', () => {
  it('applies events strictly in order', async () => {
    const applied: GraphEvent[] = [];
    const director = createDirector({
      apply: (event) => applied.push(event),
      wait: async () => {},
      instant: false,
    });

    await director.enqueue([e1, e2, e3]);

    expect(applied).toEqual([e1, e2, e3]);
  });

  it('waits the beat before applying the next event', async () => {
    vi.useFakeTimers();
    const applied: GraphEvent[] = [];
    const director = createDirector({
      apply: (event) => applied.push(event),
      wait: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
      instant: false,
    });

    const done = director.enqueue([e1, e2]);
    expect(applied).toEqual([e1]);

    await vi.advanceTimersByTimeAsync(beatDuration(e1) - 1);
    expect(applied).toEqual([e1]);

    await vi.advanceTimersByTimeAsync(1);
    expect(applied).toEqual([e1, e2]);

    await vi.advanceTimersByTimeAsync(beatDuration(e2));
    await done;
  });

  it('applies everything immediately when instant is true', async () => {
    const applied: GraphEvent[] = [];
    const director = createDirector({
      apply: (event) => applied.push(event),
      wait: async () => {},
      instant: true,
    });

    const done = director.enqueue([e1, e2, e3]);

    expect(applied).toEqual([e1, e2, e3]);
    await done;
  });

  it('cancel stops the remaining events and resolves the promise', async () => {
    vi.useFakeTimers();
    const applied: GraphEvent[] = [];
    const director = createDirector({
      apply: (event) => applied.push(event),
      wait: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
      instant: false,
    });

    const done = director.enqueue([e1, e2, e3]);
    expect(applied).toEqual([e1]);

    director.cancel();
    await vi.advanceTimersByTimeAsync(60_000);
    await done;

    expect(applied).toEqual([e1]);
  });

  it('resolves only after the last beat', async () => {
    const director = createDirector({
      apply: () => {},
      wait: async () => {},
      instant: false,
    });

    let resolved = false;
    const done = director.enqueue([e1, e2]).then(() => {
      resolved = true;
    });

    expect(resolved).toBe(false);
    await done;
    expect(resolved).toBe(true);
  });
});
