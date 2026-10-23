import { z } from 'zod';
import { schemas } from '@/api/schemas';

export const RecordedReplay = z
  .object({
    version: z.literal(1),
    label: z.string().min(1),
    description: z.string().min(1),
    recordedAt: z.iso.datetime({ offset: true }),
    source: z.string().min(1),
    farmer_id: z.string().uuid(),
    network: schemas.NetworkResponse,
    breakdown: schemas.BreakdownResponse.optional(),
  })
  .strict();

export type RecordedReplay = z.infer<typeof RecordedReplay>;

export function parseReplay(input: unknown): RecordedReplay {
  const parsed = RecordedReplay.safeParse(input);
  if (!parsed.success) {
    throw new Error(`Invalid recorded replay: ${z.prettifyError(parsed.error)}`);
  }
  return parsed.data;
}
