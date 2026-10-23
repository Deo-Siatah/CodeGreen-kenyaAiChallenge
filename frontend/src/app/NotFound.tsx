import { useI18n } from '@/i18n';

export function NotFound() {
  const { t } = useI18n();

  return (
    <main className="case-not-found">
      <h1>{t('notFound.title')}</h1>
    </main>
  );
}
