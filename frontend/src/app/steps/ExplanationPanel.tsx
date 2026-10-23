import { useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ApiError } from '@/api/errors';
import { getExplanation } from '@/api/endpoints/verification';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useI18n } from '@/i18n';

type Mode = 'farmer' | 'expert';
type Language = 'English' | 'Swahili';

export function ExplanationPanel({ sessionId }: { sessionId: string }) {
  const { t } = useI18n();
  const [mode, setMode] = useState<Mode>('farmer');
  const [language, setLanguage] = useState<Language>('English');
  const [text, setText] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  async function generate() {
    if (pending) {
      return;
    }
    const controller = new AbortController();
    controllerRef.current = controller;
    setPending(true);
    setError(null);
    try {
      const result = await getExplanation(sessionId, { mode, language }, controller.signal);
      setText(result.explanation);
    } catch (err) {
      if (err instanceof ApiError && err.kind === 'cancelled') {
        return;
      }
      setError(err instanceof ApiError ? err.message : t('explanation.error'));
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
      setPending(false);
    }
  }

  function cancel() {
    controllerRef.current?.abort();
    controllerRef.current = null;
    setPending(false);
  }

  return (
    <Card className="case-card explanation-panel">
      <CardHeader>
        <CardTitle>{t('explanation.title')}</CardTitle>
        <CardDescription>{t('explanation.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="explanation-controls">
          <label>
            {t('explanation.audience')}
            <select
              className="case-select"
              value={mode}
              onChange={(event) => setMode(event.target.value === 'expert' ? 'expert' : 'farmer')}
              disabled={pending}
            >
              <option value="farmer">{t('explanation.farmer')}</option>
              <option value="expert">{t('explanation.loanOfficer')}</option>
            </select>
          </label>
          <label>
            {t('explanation.language')}
            <select
              className="case-select"
              value={language}
              onChange={(event) => setLanguage(event.target.value === 'Swahili' ? 'Swahili' : 'English')}
              disabled={pending}
            >
              <option value="English">{t('explanation.english')}</option>
              <option value="Swahili">{t('explanation.swahili')}</option>
            </select>
          </label>
        </div>

        <div className="explanation-actions">
          {pending ? (
            <>
              <p className="case-status" role="status">
                {t('explanation.generating')}
              </p>
              <Button type="button" variant="outline" onClick={cancel}>
                {t('common.cancel')}
              </Button>
            </>
          ) : (
            <Button type="button" onClick={() => void generate()}>
              {text ? t('explanation.generateAgain') : t('explanation.generate')}
            </Button>
          )}
        </div>

        {error ? (
          <p className="ussd-handset__error" role="alert">
            {error}
          </p>
        ) : null}

        {text ? (
          <div className="explanation-text" data-testid="explanation-text">
            <ReactMarkdown>{text}</ReactMarkdown>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
