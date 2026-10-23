import { describe, expect, it } from 'vitest';
import { ApiError } from './errors';

describe('ApiError', () => {
  it('should handle validation error with fieldErrors', () => {
    const error = new ApiError('validation', 'Validation failed', 422, {
      'phone': 'Invalid phone number',
      'email': 'Invalid email'
    });
    
    expect(error.kind).toBe('validation');
    expect(error.message).toBe('Validation failed');
    expect(error.status).toBe(422);
    expect(error.fieldErrors).toEqual({
      'phone': 'Invalid phone number',
      'email': 'Invalid email'
    });
  });

  it('should handle conflict error', () => {
    const error = new ApiError('conflict', 'Resource already exists', 409);
    expect(error.kind).toBe('conflict');
    expect(error.message).toBe('Resource already exists');
    expect(error.status).toBe(409);
  });

  it('should handle not found error', () => {
    const error = new ApiError('not_found', 'Resource not found', 404);
    expect(error.kind).toBe('not_found');
    expect(error.message).toBe('Resource not found');
    expect(error.status).toBe(404);
  });

  it('should handle server error', () => {
    const error = new ApiError('server', 'Internal server error', 500);
    expect(error.kind).toBe('server');
    expect(error.message).toBe('Internal server error');
    expect(error.status).toBe(500);
  });

  it('should handle contract error', () => {
    const error = new ApiError('contract', 'Response validation failed: missing field');
    expect(error.kind).toBe('contract');
    expect(error.message).toBe('Response validation failed: missing field');
  });

  it('should handle timeout error', () => {
    const error = new ApiError('timeout', 'Request timed out');
    expect(error.kind).toBe('timeout');
    expect(error.message).toBe('Request timed out');
  });

  it('should handle network error', () => {
    const error = new ApiError('network', 'Network error');
    expect(error.kind).toBe('network');
    expect(error.message).toBe('Network error');
  });

  it('should handle cancelled error', () => {
    const error = new ApiError('cancelled', 'Request was aborted');
    expect(error.kind).toBe('cancelled');
    expect(error.message).toBe('Request was aborted');
  });
});