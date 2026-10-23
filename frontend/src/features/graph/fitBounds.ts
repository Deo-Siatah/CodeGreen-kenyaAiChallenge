import type { Point } from '@/domain/graph';

export interface ViewBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

const MIN_EXTENT = 400;

function centered(
  centerX: number,
  centerY: number,
  width: number,
  height: number,
  aspect: number,
): ViewBox {
  let w = width;
  let h = height;
  if (w / h < aspect) {
    w = h * aspect;
  } else {
    h = w / aspect;
  }
  return { x: centerX - w / 2, y: centerY - h / 2, width: w, height: h };
}

export function fitBounds(points: Point[], aspect: number, padding: number): ViewBox {
  const safeAspect = Number.isFinite(aspect) && aspect > 0 ? aspect : 1;
  const safePadding = Number.isFinite(padding) && padding > 0 ? padding : 0;

  if (points.length === 0) {
    return centered(0, 0, MIN_EXTENT, MIN_EXTENT, safeAspect);
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const point of points) {
    minX = Math.min(minX, point.x);
    minY = Math.min(minY, point.y);
    maxX = Math.max(maxX, point.x);
    maxY = Math.max(maxY, point.y);
  }

  const width = Math.max(maxX - minX + 2 * safePadding, MIN_EXTENT);
  const height = Math.max(maxY - minY + 2 * safePadding, MIN_EXTENT);
  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;

  return centered(centerX, centerY, width, height, safeAspect);
}
