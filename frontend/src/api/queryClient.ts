import { QueryClient } from '@tanstack/react-query';

// Create a single instance of QueryClient to be used throughout the app
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Retry failed queries once on kind "network" only
      retry: (failureCount, error) => {
        // Don't retry for mutations
        if (error instanceof Error && error.message.includes('validation')) {
          return false;
        }
        if (error instanceof Error && error.message.includes('not found')) {
          return false;
        }
        // Retry only once on network errors for GET queries
        if (error instanceof Error && error.message.includes('network') && failureCount === 0) {
          return true;
        }
        // Don't retry after 1 attempt or for other error types
        return false;
      },
      // Refetch data when window refocuses
      refetchOnWindowFocus: true,
      // Disable refetch in background
      refetchOnReconnect: false,
    },
    mutations: {
      // No retry for mutations
      retry: false,
    },
  },
});