import type { ComponentProps } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useI18n } from '@/i18n';

interface PendingButtonProps extends ComponentProps<typeof Button> {
  pending?: boolean;
  pendingLabel?: string;
}

export function PendingButton({
  pending = false,
  pendingLabel,
  disabled,
  children,
  ...rest
}: PendingButtonProps) {
  const { t } = useI18n();
  return (
    <Button disabled={disabled ?? pending} {...rest}>
      {pending ? (pendingLabel ?? t('common.working')) : children}
    </Button>
  );
}

interface MutationAlertProps {
  message: string | null;
  onRetry?: () => void;
}

export function MutationAlert({ message, onRetry }: MutationAlertProps) {
  const { t } = useI18n();

  if (!message) {
    return null;
  }

  return (
    <Alert variant="destructive" role="alert">
      <AlertTitle>{t('common.errorTitle')}</AlertTitle>
      <AlertDescription>
        <span>{message}</span>
        {onRetry ? (
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            {t('common.retry')}
          </Button>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
