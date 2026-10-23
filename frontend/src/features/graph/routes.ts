import type { RouteObject } from 'react-router-dom';

export function replayRoute(): RouteObject[] {
  return [
    {
      path: '/replay',
      lazy: async () => {
        const module = await import('./ReplayPage');
        return { Component: module.ReplayPage };
      },
    },
  ];
}
