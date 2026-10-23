import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type Simulation,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force';
import { motionValue, type MotionValue } from 'motion/react';
import { useEffect, useMemo, useRef } from 'react';
import { ringTarget, type GraphEdge, type GraphNode, type NodeKind } from '@/domain/graph';
import { KIND_STYLE } from './kindStyles';

export interface LayoutNode extends SimulationNodeDatum {
  id: string;
  kind: NodeKind;
  targetX: number;
  targetY: number;
}

export interface LayoutLink extends SimulationLinkDatum<LayoutNode> {
  id: string;
  kind: GraphEdge['kind'];
  source: string | LayoutNode;
  target: string | LayoutNode;
}

export type LayoutSimulation = Simulation<LayoutNode, LayoutLink>;

export interface NodePosition {
  x: MotionValue<number>;
  y: MotionValue<number>;
}

export interface ForceLayout {
  simulation: LayoutSimulation;
  positions: Map<string, NodePosition>;
  nodeById: Record<string, LayoutNode>;
}

function ensurePosition(positions: Map<string, NodePosition>, id: string): NodePosition {
  const existing = positions.get(id);
  if (existing) {
    return existing;
  }
  const created: NodePosition = { x: motionValue(0), y: motionValue(0) };
  positions.set(id, created);
  return created;
}

function buildLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  positions: Map<string, NodePosition>,
): ForceLayout {
  const ordered = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
  const kindIndex = new Map<NodeKind, number>();
  const kindTotal = new Map<NodeKind, number>();
  for (const node of ordered) {
    kindTotal.set(node.kind, (kindTotal.get(node.kind) ?? 0) + 1);
  }

  const layoutNodes: LayoutNode[] = ordered.map((node) => {
    const index = kindIndex.get(node.kind) ?? 0;
    kindIndex.set(node.kind, index + 1);
    const target = ringTarget(node.kind, index, kindTotal.get(node.kind) ?? 1);
    const existed = positions.has(node.id);
    const position = ensurePosition(positions, node.id);

    return {
      id: node.id,
      kind: node.kind,
      targetX: target.x,
      targetY: target.y,
      x: existed ? position.x.get() : target.x,
      y: existed ? position.y.get() : target.y,
    };
  });

  const links: LayoutLink[] = edges.map((edge) => ({
    id: edge.id,
    kind: edge.kind,
    source: edge.from,
    target: edge.to,
  }));

  const simulation = forceSimulation<LayoutNode>(layoutNodes)
    .force(
      'link',
      forceLink<LayoutNode, LayoutLink>(links)
        .id((node) => node.id)
        .distance(90)
        .strength(0.35),
    )
    .force('charge', forceManyBody<LayoutNode>().strength(-140))
    .force(
      'collide',
      forceCollide<LayoutNode>().radius((node) => KIND_STYLE[node.kind].radius + 8),
    )
    .force('x', forceX<LayoutNode>((node) => node.targetX).strength(0.06))
    .force('y', forceY<LayoutNode>((node) => node.targetY).strength(0.06))
    .alphaTarget(0.02)
    .stop();

  const nodeById: Record<string, LayoutNode> = {};
  for (const node of layoutNodes) {
    nodeById[node.id] = node;
  }

  simulation.on('tick', () => {
    for (const node of layoutNodes) {
      const position = ensurePosition(positions, node.id);
      position.x.set(node.x ?? node.targetX);
      position.y.set(node.y ?? node.targetY);
    }
  });

  return { simulation, positions, nodeById };
}

export interface UseForceLayoutOptions {
  reducedMotion: boolean;
}

export function useForceLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  options: UseForceLayoutOptions,
): ForceLayout {
  const positionsRef = useRef<Map<string, NodePosition>>(new Map());

  const layout = useMemo(
    () => buildLayout(nodes, edges, positionsRef.current),
    [nodes, edges],
  );

  useEffect(() => {
    const { simulation } = layout;
    const settleOnly = options.reducedMotion || import.meta.env.MODE === 'test';

    if (settleOnly) {
      simulation.tick(120);
      simulation.stop();
      return undefined;
    }

    let frame = 0;
    const step = () => {
      simulation.tick();
      frame = requestAnimationFrame(step);
    };
    simulation.alphaTarget(0.02).restart();
    frame = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(frame);
      simulation.stop();
    };
  }, [layout, options.reducedMotion]);

  return layout;
}
