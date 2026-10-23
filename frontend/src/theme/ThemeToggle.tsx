import { Moon, Sun } from 'lucide-react';
import { useI18n } from '@/i18n';
import { useTheme } from './useTheme';
import './theme-toggle.css';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useI18n();
  const target = theme === 'dark' ? 'light' : 'dark';
  const label =
    target === 'light' ? t('theme.switchToLight') : t('theme.switchToDark');
  const Icon = target === 'light' ? Sun : Moon;

  return (
    <button
      type="button"
      className="theme-toggle"
      aria-label={label}
      title={label}
      onClick={toggleTheme}
    >
      <Icon size={16} aria-hidden="true" />
    </button>
  );
}
