import type { z } from 'zod';
import { ApiError } from './errors';

/**
 * Single response-validation boundary. Every API response is parsed here so a
 * backend contract drift surfaces as ApiError("contract") instead of a raw
 * ZodError leaking into a component.
 */
export function validate<T>(schema: z.ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new ApiError(
      'contract',
      `Response validation failed: ${result.error.message}`,
    );
  }
  return result.data;
}
