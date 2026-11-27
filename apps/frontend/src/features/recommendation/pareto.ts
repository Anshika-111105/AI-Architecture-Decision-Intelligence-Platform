import type { Better } from '../predictions/metrics'

export interface Point {
  id: string
  x: number
  y: number
}

const atLeastAsGood = (a: number, b: number, better: Better) => (better === 'lower' ? a <= b : a >= b)
const strictlyBetter = (a: number, b: number, better: Better) => (better === 'lower' ? a < b : a > b)

/**
 * Ids of the points on the Pareto frontier for two objectives: those that no other
 * point beats on one objective without being worse on the other. Identical points
 * are all kept.
 */
export function paretoFront(points: Point[], xBetter: Better, yBetter: Better): Set<string> {
  const front = new Set<string>()
  for (const p of points) {
    const dominated = points.some(
      (q) =>
        q !== p &&
        atLeastAsGood(q.x, p.x, xBetter) &&
        atLeastAsGood(q.y, p.y, yBetter) &&
        (strictlyBetter(q.x, p.x, xBetter) || strictlyBetter(q.y, p.y, yBetter)),
    )
    if (!dominated) front.add(p.id)
  }
  return front
}
