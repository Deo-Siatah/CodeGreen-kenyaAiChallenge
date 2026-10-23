import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useI18n } from '@/i18n';

interface StepPlaceholderProps {
  title: string;
  description: string;
}

export function StepPlaceholder({ title, description }: StepPlaceholderProps) {
  const { t } = useI18n();

  return (
    <Card className="case-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="case-placeholder">{t('case.placeholder.coming')}</p>
      </CardContent>
    </Card>
  );
}
