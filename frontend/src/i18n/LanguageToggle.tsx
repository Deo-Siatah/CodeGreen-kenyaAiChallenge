import { useI18n } from './index';
import './language-toggle.css';

export function LanguageToggle() {
  const { language, t, toggleLanguage } = useI18n();
  const target = language === 'en' ? 'sw' : 'en';
  const label =
    target === 'sw' ? t('language.switchToSwahili') : t('language.switchToEnglish');

  return (
    <button
      type="button"
      className="language-toggle"
      aria-label={label}
      title={label}
      onClick={toggleLanguage}
    >
      <span aria-hidden="true">{target === 'sw' ? 'SW' : 'EN'}</span>
    </button>
  );
}
