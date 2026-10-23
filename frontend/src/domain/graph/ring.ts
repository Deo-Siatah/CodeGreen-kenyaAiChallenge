import type { NodeKind, VerifierKind } from './types';

export interface Point {
  x: number;
  y: number;
}

const RING2_KINDS: VerifierKind[] = ['trust_source', 'market_actor', 'social_group'];
const RING2_SECTOR_DEGREES = 120;

// Radii are fixed and large enough that 12 nodes packed into one 120 degree
// sector keep at least 56px between neighbours:
//   2 * 340 * sin(5deg) ~= 59px.
const RADIUS: Record<Exclude<NodeKind, 'farmer'>, number> = {
  farm: 200,
  trust_source: 340,
  market_actor: 340,
  social_group: 340,
  loan: 420,
};

function onRing(radius: number, angleDegrees: number): Point {
  const angle = (angleDegrees * Math.PI) / 180;
  return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) };
}

function isRing2Kind(kind: NodeKind): kind is VerifierKind {
  return kind === 'trust_source' || kind === 'market_actor' || kind === 'social_group';
}

export function ringTarget(kind: NodeKind, index: number, count: number): Point {
  if (kind === 'farmer') {
    return { x: 0, y: 0 };
  }

  const radius = RADIUS[kind];
  const safeCount = Math.max(1, count);

  if (isRing2Kind(kind)) {
    const sector = RING2_KINDS.indexOf(kind);
    const offset = sector * RING2_SECTOR_DEGREES;
    const angle = offset + ((index + 0.5) * RING2_SECTOR_DEGREES) / safeCount;
    return onRing(radius, angle);
  }

  const offset = kind === 'farm' ? -90 : 0;
  const angle = offset + (index * 360) / safeCount;
  return onRing(radius, angle);
}
