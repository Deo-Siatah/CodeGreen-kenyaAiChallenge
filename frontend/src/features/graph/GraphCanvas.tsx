import { useCallback, useEffect, useMemo, useRef } from 'react';
import { motion, useAnimationFrame, useMotionValue, useTransform } from 'motion/react';
import {
  Banknote,
  ShieldCheck,
  Sprout,
  Store,
  Users,
  Wheat,
  type LucideIcon,
} from 'lucide-react';
import type { GraphEdge, GraphNode, NodeKind } from '@/domain/graph';
import { useI18n } from '@/i18n';
import { phaseLabel } from '@/i18n/labels';
import { describeEvent } from './narration';
import { fitBounds } from './fitBounds';
import { kindColor, stateColor, KIND_STYLE } from './kindStyles';
import { PULSE_MS, useGraphStore, type Pulse } from './store';
import { useForceLayout, type LayoutSimulation, type NodePosition } from './useForceLayout';
import { useReducedMotionPreference } from './useReducedMotion';
import './graph.css';

const KIND_ICON: Record<NodeKind, LucideIcon> = {
  farmer: Sprout,
  farm: Wheat,
  trust_source: ShieldCheck,
  market_actor: Store,
  social_group: Users,
  loan: Banknote,
};

type Positions = Map<string, NodePosition>;

export interface GraphCanvasProps {
  onSimulationReady?: (simulation: LayoutSimulation) => void;
}

function poolPositions(positions: Positions, id: string): NodePosition | undefined {
  return positions.get(id);
}

function NodeView({ node, positions }: { node: GraphNode; positions: Positions }) {
  const fallbackX = useMotionValue(0);
  const fallbackY = useMotionValue(0);
  const position = poolPositions(positions, node.id);
  const x = position ? position.x : fallbackX;
  const y = position ? position.y : fallbackY;

  const radius = KIND_STYLE[node.kind].radius;
  const Icon = KIND_ICON[node.kind];
  const stroke = stateColor(node.state, node.rating);

  return (
    <motion.g
      className="graph-node"
      data-testid={`node-${node.id}`}
      style={{ x, y }}
    >
      <circle
        r={radius}
        fill={kindColor(node.kind)}
        fillOpacity={0.16}
        stroke={stroke}
        strokeWidth={2}
      />
      <g transform={`translate(${-radius}, ${-radius})`} pointerEvents="none">
        <Icon size={radius * 2} color={stroke} strokeWidth={1.5} />
      </g>
      <text className="graph-node__label" y={radius + 16} textAnchor="middle">
        {node.label}
      </text>
    </motion.g>
  );
}

function EdgeView({ edge, positions }: { edge: GraphEdge; positions: Positions }) {
  const zero = useMotionValue(0);
  const from = poolPositions(positions, edge.from);
  const to = poolPositions(positions, edge.to);

  const d = useTransform(
    [
      from ? from.x : zero,
      from ? from.y : zero,
      to ? to.x : zero,
      to ? to.y : zero,
    ],
    ([x1, y1, x2, y2]) => `M ${x1} ${y1} L ${x2} ${y2}`,
  );

  const stroke = edge.kind === 'evidence' ? 'hsl(var(--edge-evidence))' : 'hsl(var(--edge-line))';

  return (
    <motion.path
      className="graph-edge"
      data-testid={`edge-${edge.id}`}
      d={d}
      fill="none"
      stroke={stroke}
      strokeOpacity={edge.kind === 'evidence' ? 0.7 : 0.35}
      strokeWidth={edge.kind === 'evidence' ? 2 : 1.25}
    />
  );
}

function PulseView({ pulse, positions }: { pulse: Pulse; positions: Positions }) {
  const cx = useMotionValue(0);
  const cy = useMotionValue(0);
  const start = useRef<number | null>(null);

  const from = poolPositions(positions, pulse.from);
  const to = poolPositions(positions, pulse.to);

  useAnimationFrame((time) => {
    if (start.current === null) {
      start.current = time;
    }
    const fromX = from ? from.x.get() : 0;
    const fromY = from ? from.y.get() : 0;
    const toX = to ? to.x.get() : 0;
    const toY = to ? to.y.get() : 0;
    const progress = (((time - start.current) % PULSE_MS) + PULSE_MS) % PULSE_MS / PULSE_MS;
    const t = pulse.kind === 'back' ? 1 - progress : progress;
    cx.set(fromX + (toX - fromX) * t);
    cy.set(fromY + (toY - fromY) * t);
  });

  return (
    <motion.circle
      className="graph-pulse"
      data-testid={`pulse-${pulse.id}`}
      cx={cx}
      cy={cy}
      r={6}
      fill={pulse.kind === 'back' ? 'hsl(var(--state-responded-gold))' : 'hsl(var(--node-glow))'}
    />
  );
}

export function GraphCanvas({ onSimulationReady }: GraphCanvasProps) {
  const { t } = useI18n();
  const nodes = useGraphStore((state) => state.nodes);
  const edges = useGraphStore((state) => state.edges);
  const pulses = useGraphStore((state) => state.pulses);
  const log = useGraphStore((state) => state.log);
  const phase = useGraphStore((state) => state.phase);
  const score = useGraphStore((state) => state.score);

  const reducedMotion = useReducedMotionPreference();

  const nodeList = useMemo(() => Object.values(nodes), [nodes]);
  const edgeList = useMemo(() => Object.values(edges), [edges]);

  const { simulation, positions } = useForceLayout(nodeList, edgeList, { reducedMotion });

  const svgRef = useRef<SVGSVGElement | null>(null);

  const updateViewBox = useCallback(() => {
    const svg = svgRef.current;
    if (!svg) {
      return;
    }
    const rect = svg.getBoundingClientRect();
    const aspect = rect.width > 0 && rect.height > 0 ? rect.width / rect.height : 1;
    const points = nodeList.map((node) => {
      const position = poolPositions(positions, node.id);
      return { x: position ? position.x.get() : 0, y: position ? position.y.get() : 0 };
    });
    const box = fitBounds(points, aspect, 90);
    svg.setAttribute('viewBox', `${box.x} ${box.y} ${box.width} ${box.height}`);
  }, [nodeList, positions]);

  useAnimationFrame(updateViewBox);

  useEffect(() => {
    updateViewBox();
  }, [updateViewBox]);

  useEffect(() => {
    onSimulationReady?.(simulation);
  }, [onSimulationReady, simulation]);

  const announcement = log.map((event) => describeEvent(event, t)).join(' ');

  return (
    <div className="graph-shell">
      <svg
        ref={svgRef}
        className="graph-canvas"
        role="img"
        aria-label={t('case.graph.aria', {
          nodes: nodeList.length,
          edges: edgeList.length,
        })}
      >
        <g className="graph-layer graph-layer--edges">
          {edgeList.map((edge) => (
            <EdgeView key={edge.id} edge={edge} positions={positions} />
          ))}
        </g>
        <g className="graph-layer graph-layer--nodes">
          {nodeList.map((node) => (
            <NodeView key={node.id} node={node} positions={positions} />
          ))}
        </g>
        {!reducedMotion && (
          <g className="graph-layer graph-layer--pulses">
            {pulses.map((pulse) => (
              <PulseView key={pulse.id} pulse={pulse} positions={positions} />
            ))}
          </g>
        )}
      </svg>

      <div className="graph-hud">
        <span className="graph-hud__phase">{phaseLabel(phase, t)}</span>
        {score && <span>{t('case.graph.final', { score: score.final })}</span>}
      </div>

      <div className="graph-aria-log" data-testid="aria-log" aria-live="polite">
        {announcement}
      </div>
    </div>
  );
}
