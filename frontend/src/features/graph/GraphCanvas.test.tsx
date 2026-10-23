import { Profiler } from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GraphCanvas } from './GraphCanvas';
import { useGraphStore, type Pulse } from './store';
import { describeEvent } from './narration';
import type { LayoutSimulation } from './useForceLayout';
import { graphReducer, initialState, type GraphEvent, type GraphState } from '@/domain/graph';
import { liveFlowEvents } from '@/test/graph-fixture';

function fold(events: GraphEvent[]): GraphState {
  return events.reduce((state, event) => graphReducer(state, event), initialState);
}

function seed(state: GraphState, extra: { log?: GraphEvent[]; pulses?: Pulse[] } = {}) {
  useGraphStore.setState({
    ...state,
    log: extra.log ?? [],
    pulses: extra.pulses ?? [],
    playing: false,
    instant: true,
  });
}

const originalMatchMedia = window.matchMedia;

function mockReducedMotion(reduce: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: reduce && query.includes('prefers-reduced-motion'),
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

beforeEach(() => {
  mockReducedMotion(false);
});

afterEach(() => {
  window.matchMedia = originalMatchMedia;
  vi.restoreAllMocks();
});

describe('GraphCanvas', () => {
  it('3. renders exactly one node element per node and one edge element per edge', () => {
    const state = fold(liveFlowEvents);
    seed(state);

    const { container } = render(<GraphCanvas />);

    const nodeElements = container.querySelectorAll('[data-testid^="node-"]');
    const edgeElements = container.querySelectorAll('[data-testid^="edge-"]');

    expect(nodeElements).toHaveLength(Object.keys(state.nodes).length);
    expect(edgeElements).toHaveLength(Object.keys(state.edges).length);
  });

  it('4. force-layout ticks do not cause React commits', async () => {
    seed(fold(liveFlowEvents));

    let commits = 0;
    const simRef: { current: LayoutSimulation | null } = { current: null };

    render(
      <Profiler
        id="graph"
        onRender={() => {
          commits += 1;
        }}
      >
        <GraphCanvas
          onSimulationReady={(simulation) => {
            simRef.current = simulation;
          }}
        />
      </Profiler>,
    );

    await waitFor(() => expect(simRef.current).not.toBeNull());

    commits = 0;
    act(() => {
      for (let i = 0; i < 100; i += 1) {
        simRef.current?.tick();
      }
    });

    expect(commits).toBeLessThan(5);
  });

  it('5. reduced motion mounts no travelling pulses', () => {
    const pulses: Pulse[] = [
      { id: 'pulse-1', from: 'farmer', to: 'trust', kind: 'out' },
      { id: 'pulse-2', from: 'market', to: 'farmer', kind: 'back' },
    ];

    mockReducedMotion(false);
    seed(fold(liveFlowEvents), { pulses });
    const { container: moving, unmount } = render(<GraphCanvas />);
    expect(moving.querySelectorAll('[data-testid^="pulse-"]')).toHaveLength(2);
    unmount();

    mockReducedMotion(true);
    seed(fold(liveFlowEvents), { pulses });
    const { container: still } = render(<GraphCanvas />);
    expect(still.querySelectorAll('[data-testid^="pulse-"]')).toHaveLength(0);
  });

  it('6. the aria-live log announces a sentence per applied event', () => {
    seed(fold(liveFlowEvents), { log: liveFlowEvents });

    render(<GraphCanvas />);

    const log = screen.getByTestId('aria-log');
    const text = log.textContent ?? '';

    for (const event of liveFlowEvents) {
      expect(text).toContain(describeEvent(event));
    }
  });

  it('exposes the canvas as an image with a summary label', () => {
    const state = fold(liveFlowEvents);
    seed(state);

    render(<GraphCanvas />);

    const canvas = screen.getByRole('img');
    expect(canvas).toHaveAttribute('aria-label');
    expect(canvas.getAttribute('aria-label')).toContain(String(Object.keys(state.nodes).length));
  });
});
