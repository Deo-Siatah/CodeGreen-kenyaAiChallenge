import { render } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { createAppRoutes } from '@/app/router';
import { graphReducer, initialState, type GraphEvent, type GraphState } from '@/domain/graph';
import { useGraphStore } from '@/features/graph/store';
import { I18nProvider, type Language } from '@/i18n';

export function seedGraph(events: GraphEvent[]): GraphState {
  const state = events.reduce((current, event) => graphReducer(current, event), initialState);
  useGraphStore.setState({
    ...state,
    log: [],
    pulses: [],
    playing: false,
    instant: true,
  });
  return state;
}

export function resetGraph(): void {
  useGraphStore.setState({ ...initialState, log: [], pulses: [], playing: false, instant: true });
}

export function renderCase(path: string, options?: { language?: Language }) {
  useGraphStore.setState({ instant: true });
  const router = createMemoryRouter(createAppRoutes(), { initialEntries: [path] });
  const app = <RouterProvider router={router} />;
  const utils = render(
    options?.language ? (
      <I18nProvider initialLanguage={options.language}>{app}</I18nProvider>
    ) : (
      app
    ),
  );
  return { router, ...utils };
}
