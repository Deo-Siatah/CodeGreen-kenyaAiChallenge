import { describe, expect, it } from 'vitest';
import { ApiError } from './errors';

describe('ApiError', () => {
  it('should create error with correct properties', () => {
    const error = new ApiError('validation', 'Test error', 422, { field: 'error message' });
    expect(error.kind).toBe('validation');
    expect(error.message).toBe('Test error');
    expect(error.status).toBe(422);
    expect(error.fieldErrors).toEqual({ field: 'error message' });
  });

  it('should create error without fieldErrors', () => {
    const error = new ApiError('server', 'Server error', 500);
    expect(error.kind).toBe('server');
    expect(error.message).toBe('Server error');
    expect(error.status).toBe(500);
    expect(error.fieldErrors).toBeUndefined();
  });

  it('should create error without status', () => {
    const error = new ApiError('network', 'Network error');
    expect(error.kind).toBe('network');
    expect(error.message).toBe('Network error');
    expect(error.status).toBeUndefined();
  });
});