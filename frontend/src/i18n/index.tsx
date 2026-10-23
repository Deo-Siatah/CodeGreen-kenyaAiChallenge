import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { makeTranslator, type Language, type Translator } from './dictionary';

export { translate } from './dictionary';
export type { Language, TranslationKey, Translator, TranslationVars } from './dictionary';

const STORAGE_KEY = 'hifadhi.language';

interface I18nContextValue {
  language: Language;
  locale: string;
  t: Translator;
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
}

function isLanguage(value: unknown): value is Language {
  return value === 'en' || value === 'sw';
}

function readStoredLanguage(): Language | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return isLanguage(stored) ? stored : null;
  } catch {
    return null;
  }
}

const defaultTranslator = makeTranslator('en');

const I18nContext = createContext<I18nContextValue>({
  language: 'en',
  locale: 'en-KE',
  t: defaultTranslator,
  setLanguage: () => undefined,
  toggleLanguage: () => undefined,
});

interface I18nProviderProps {
  children: ReactNode;
  initialLanguage?: Language;
}

export function I18nProvider({ children, initialLanguage }: I18nProviderProps) {
  const [language, setLanguage] = useState<Language>(
    () => initialLanguage ?? readStoredLanguage() ?? 'en',
  );

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      window.localStorage.setItem(STORAGE_KEY, language);
    } catch {
      return;
    }
  }, [language]);

  const toggleLanguage = useCallback(() => {
    setLanguage((current) => (current === 'en' ? 'sw' : 'en'));
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      locale: language === 'sw' ? 'sw-KE' : 'en-KE',
      t: makeTranslator(language),
      setLanguage,
      toggleLanguage,
    }),
    [language, toggleLanguage],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
