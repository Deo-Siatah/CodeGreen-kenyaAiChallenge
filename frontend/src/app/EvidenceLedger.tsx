import { useRequestLog } from '@/api/requestLog';
import { useI18n } from '@/i18n';

export function EvidenceLedger() {
  const { t } = useI18n();
  const entries = useRequestLog((state) => state.entries);

  return (
    <section className="case-ledger" data-testid="ledger" aria-label={t('evidence.aria')}>
      <h2>{t('evidence.title')}</h2>
      {entries.length === 0 ? (
        <p className="case-ledger__empty">{t('evidence.empty')}</p>
      ) : (
        <ol>
          {entries.map((entry) => (
            <li key={entry.id} data-testid="ledger-entry" data-ok={entry.ok}>
              <span className="case-ledger__method">{entry.method}</span>
              <span className="case-ledger__path">{entry.path}</span>
              <span className="case-ledger__status">{entry.status ?? 'ERR'}</span>
              <span className="case-ledger__duration">{entry.durationMs}ms</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
