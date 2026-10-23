// Export the client instance
export { client } from './client';

// Export the ApiError class
export { ApiError } from './errors';

// Export all schemas
export { schemas } from './schemas';

// Export query client
export { queryClient } from './queryClient';

// Export all endpoint functions
// Farmers
export * from './endpoints/farmers';

// Stats
export * from './endpoints/stats';

// Trust
export * from './endpoints/trust';

// Verification
export * from './endpoints/verification';

// Loans
export * from './endpoints/loans';