import axios, {
  AxiosError,
  type AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { ApiError } from './errors';
import { recordRequest } from './requestLog';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const client: AxiosInstance = axios.create({
  baseURL,
  timeout: 20000,
});

const startedAt = new WeakMap<InternalAxiosRequestConfig, number>();

function now(): number {
  return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

function record(config: InternalAxiosRequestConfig, status: number | null): void {
  const start = startedAt.get(config) ?? now();
  recordRequest({
    at: Date.now(),
    method: (config.method ?? 'get').toUpperCase(),
    path: config.url ?? '',
    status,
    durationMs: Math.round(now() - start),
    ok: status !== null && status >= 200 && status < 300,
  });
}

// Single authentication seam. When auth lands, attach the token here.
client.interceptors.request.use((config) => {
  startedAt.set(config, now());
  return config;
});

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function detailOf(data: unknown): unknown {
  return isRecord(data) ? data.detail : undefined;
}

function detailMessage(data: unknown, fallback: string): string {
  const detail = detailOf(data);
  return typeof detail === 'string' ? detail : fallback;
}

function fieldErrorsFrom(detail: unknown): Record<string, string> {
  const fieldErrors: Record<string, string> = {};
  if (!Array.isArray(detail)) {
    return fieldErrors;
  }

  for (const item of detail) {
    if (!isRecord(item)) {
      continue;
    }
    const { loc, msg } = item;
    if (Array.isArray(loc) && loc.length > 1 && typeof msg === 'string') {
      fieldErrors[loc.slice(1).map(String).join('.')] = msg;
    }
  }

  return fieldErrors;
}

function firstValidationMessage(detail: unknown): string {
  if (Array.isArray(detail)) {
    const [first] = detail;
    if (isRecord(first) && typeof first.msg === 'string') {
      return first.msg;
    }
  }
  return 'Validation failed';
}

// Failures are normalised into ApiError. Response bodies are validated in the
// endpoint modules with `validate()`, not here, so each endpoint owns exactly
// one contract.
client.interceptors.response.use(
  (response: AxiosResponse) => {
    record(response.config, response.status);
    return response;
  },
  (error: AxiosError) => {
    if (error.config) {
      record(error.config, error.response?.status ?? null);
    }

    if (error.name === 'CanceledError' || error.code === 'ABORT_ERR') {
      throw new ApiError('cancelled', 'Request was aborted');
    }

    if (error.code === 'ECONNABORTED') {
      throw new ApiError('timeout', 'Request timed out');
    }

    if (error.code === 'ERR_NETWORK') {
      throw new ApiError('network', 'Network error');
    }

    if (error.response) {
      const { status } = error.response;
      const data: unknown = error.response.data;
      const detail = detailOf(data);

      if (status === 422 && Array.isArray(detail)) {
        throw new ApiError(
          'validation',
          firstValidationMessage(detail),
          status,
          fieldErrorsFrom(detail),
        );
      }

      if (status === 409) {
        throw new ApiError('conflict', detailMessage(data, 'Conflict'), status);
      }

      if (status === 404) {
        throw new ApiError('not_found', detailMessage(data, 'Not found'), status);
      }

      if (status >= 500) {
        throw new ApiError('server', detailMessage(data, 'Server error'), status);
      }

      throw new ApiError('server', detailMessage(data, 'Request failed'), status);
    }

    throw new ApiError('network', 'Unknown network error');
  },
);
