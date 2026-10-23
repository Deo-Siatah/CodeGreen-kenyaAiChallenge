import { Link } from 'react-router-dom';
import { useI18n } from '@/i18n';
import { LanguageToggle } from '@/i18n/LanguageToggle';
import { ThemeToggle } from '@/theme';
import './product-header.css';

interface ProductHeaderProps {
  active: 'portfolio' | 'dashboard';
}

export function ProductHeader({ active }: ProductHeaderProps) {
  const { t } = useI18n();

  return (
    <header className="product-header">
      <Link to="/" className="product-brand" aria-label={t('app.brandAria')}>
        <span className="product-brand__mark" aria-hidden="true">
          H
        </span>
        <span className="product-brand__name">Hifadhi</span>
        <span className="product-brand__tag">{t('app.tagline')}</span>
      </Link>
      <nav className="product-nav" aria-label={t('nav.aria')}>
        <Link
          to="/"
          className="product-nav__link"
          aria-current={active === 'portfolio' ? 'page' : undefined}
        >
          {t('nav.portfolio')}
        </Link>
        <Link
          to="/ui"
          className="product-nav__link"
          aria-current={active === 'dashboard' ? 'page' : undefined}
        >
          {t('nav.dashboard')}
        </Link>
        <LanguageToggle />
        <ThemeToggle />
        <Link to="/case/new" className="product-nav__cta">
          {t('nav.newCase')}
        </Link>
      </nav>
    </header>
  );
}
