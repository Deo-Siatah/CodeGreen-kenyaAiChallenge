import { eventsFromNetwork, type GraphEvent } from '@/domain/graph';
import graceWanjiku from './grace-wanjiku.json';
import { parseReplay, type RecordedReplay } from './schema';

export const defaultReplay = parseReplay(graceWanjiku);

export function replayEvents(replay: RecordedReplay): GraphEvent[] {
  return eventsFromNetwork(replay.network);
}

export { parseReplay };
export type { RecordedReplay } from './schema';
