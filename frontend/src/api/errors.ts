export type ApiErrorKind =
  | 'validation'
  | 'conflict'
  | 'not_found'
  | 'server'
  | 'network'
  | 'timeout'
  | 'cancelled'
  | 'contract';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | undefined;
  readonly fieldErrors: Record<string, string> | undefined;

  constructor(
    kind: ApiErrorKind,
    message: string,
    status?: number,
    fieldErrors?: Record<string, string>,
  ) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}
