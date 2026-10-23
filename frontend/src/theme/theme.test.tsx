import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';
import { I18nProvider } from '@/i18n';
import { ThemeProvider } from './ThemeProvider';
import { THEME_STORAGE_KEY } from './theme';
import { ThemeToggle } from './ThemeToggle';
import { useTheme } from './useTheme';

function ThemeProbe() {
  const { theme } = useTheme();
  return <span data-testid="theme">{theme}</span>;
}

afterEach(() => {
  window.localStorage.clear();
  document.documentElement.classList.remove('dark');
  document.documentElement.style.colorScheme = '';
});

describe('theme', () => {
  it('defaults to dark and toggles to light', async () => {
    const user = userEvent.setup({ delay: null });
    render(
      <I18nProvider>
        <ThemeProvider>
          <ThemeToggle />
          <ThemeProbe />
        </ThemeProvider>
      </I18nProvider>,
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    expect(document.documentElement).toHaveClass('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');

    await user.click(screen.getByRole('button', { name: /switch to light mode/i }));

    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(document.documentElement).not.toHaveClass('dark');
    expect(document.documentElement.style.colorScheme).toBe('light');
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe('light');
    expect(
      screen.getByRole('button', { name: /switch to dark mode/i }),
    ).toBeInTheDocument();
  });

  it('restores a stored light preference and ignores invalid values', () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, 'light');
    const { unmount } = render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('light');
    expect(document.documentElement).not.toHaveClass('dark');

    unmount();
    window.localStorage.setItem(THEME_STORAGE_KEY, 'sepia');
    render(
      <ThemeProvider>
        <ThemeProbe />
      </ThemeProvider>,
    );

    expect(screen.getByTestId('theme')).toHaveTextContent('dark');
    expect(document.documentElement).toHaveClass('dark');
  });
});
