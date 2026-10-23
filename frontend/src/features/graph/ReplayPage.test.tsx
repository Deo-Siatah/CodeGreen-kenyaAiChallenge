import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it } from 'vitest';
import { I18nProvider } from '@/i18n';
import { defaultReplay } from '@/replay';
import { ReplayPage } from './ReplayPage';
import { useGraphStore } from './store';

afterEach(() => {
  useGraphStore.getState().reset();
});

describe('ReplayPage', () => {
  it('labels the recording and fast-forwards through its events', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <I18nProvider>
        <MemoryRouter>
          <ReplayPage />
        </MemoryRouter>
      </I18nProvider>,
    );

    expect(screen.getByRole('heading', { name: /recorded replay/i })).toBeInTheDocument();
    expect(screen.getByText(/Grace Wanjiku/)).toBeInTheDocument();
    expect(screen.getByText(/api\/farmers/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /fast-forward/i }));

    await waitFor(() => {
      expect(useGraphStore.getState().nodes[defaultReplay.farmer_id]?.label).toBe(
        'Grace Wanjiku',
      );
    });

    const loan = Object.values(useGraphStore.getState().nodes).find(
      (node) => node.kind === 'loan',
    );
    expect(loan?.meta.status).toBe('repaid');

    await waitFor(() => {
      expect(screen.getByTestId('replay-score')).toHaveTextContent('89.8');
    });
    expect(screen.getByTestId('replay-calculation')).toHaveTextContent(
      'Character 95.0 × 60% + Capacity 82.0 × 40% = 89.8',
    );
    expect(screen.getByTestId('replay-translation-en')).toHaveTextContent(
      /Grace Wanjiku scores 95\.0 on character evidence/,
    );
    expect(screen.getByTestId('replay-translation-sw')).toHaveTextContent(
      /ana alama 95\.0 kwa ushahidi wa tabia/,
    );

    await user.click(screen.getByRole('button', { name: /switch to kiswahili/i }));
    expect(
      screen.getByRole('heading', { name: /uchezaji uliorekodiwa/i }),
    ).toBeInTheDocument();
  });
});
