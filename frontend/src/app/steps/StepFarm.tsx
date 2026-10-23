import { useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ApiError } from '@/api/errors';
import { createFarm } from '@/api/endpoints/farmers';
import type { FarmRouteCreate } from '@/api/schemas';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useGraphStore } from '@/features/graph/store';
import { useI18n } from '@/i18n';
import { presetLabel } from '@/i18n/labels';
import { useCaseStore } from '../caseStore';
import { MutationAlert, PendingButton } from '../controls';
import { LOCATION_PRESETS, PRODUCTION_TYPES } from '../presets';
import {
  createFarmFormSchema,
  farmFormSchema,
  toFarmBody,
  type FarmFormValues,
} from './formSchemas';

const DEFAULT_VALUES: FarmFormValues = {
  acreage: '',
  production_type: '',
  latitude: '',
  longitude: '',
};

function isFarmField(key: string): key is keyof FarmFormValues {
  return key in farmFormSchema.shape;
}

export function StepFarm() {
  const { t } = useI18n();
  const caseId = useCaseStore((state) => state.caseId);
  const setStep = useCaseStore((state) => state.setStep);
  const dispatch = useGraphStore((state) => state.dispatch);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastBody = useRef<FarmRouteCreate | null>(null);
  const inFlight = useRef(false);

  const schema = useMemo(() => createFarmFormSchema(t), [t]);

  const form = useForm<FarmFormValues>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULT_VALUES,
  });

  async function send(body: FarmRouteCreate): Promise<void> {
    if (inFlight.current || !caseId) {
      return;
    }
    inFlight.current = true;
    setPending(true);
    setError(null);

    try {
      const farm = await createFarm(caseId, body);
      await dispatch([
        {
          type: 'FARM_CREATED',
          farmId: farm.id,
          farmerId: caseId,
          acreage: farm.acreage,
          latitude: farm.latitude,
          longitude: farm.longitude,
        },
      ]);
      setStep(3);
    } catch (err) {
      if (err instanceof ApiError && err.kind === 'validation' && err.fieldErrors) {
        let mapped = false;
        for (const [field, message] of Object.entries(err.fieldErrors)) {
          if (isFarmField(field)) {
            form.setError(field, { type: 'server', message });
            mapped = true;
          }
        }
        if (!mapped) {
          setError(err.message);
        }
      } else {
        setError(err instanceof ApiError ? err.message : t('common.unexpectedError'));
      }
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  function onSubmit() {
    const body = toFarmBody(form.getValues());
    lastBody.current = body;
    void send(body);
  }

  return (
    <Card className="case-card">
      <CardHeader>
        <CardTitle>{t('case.farm.title')}</CardTitle>
        <CardDescription>{t('case.farm.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="case-presets">
          {LOCATION_PRESETS.map((preset) => (
            <Button
              key={preset.name}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                form.setValue('latitude', String(preset.latitude), { shouldValidate: true });
                form.setValue('longitude', String(preset.longitude), { shouldValidate: true });
              }}
            >
              {t('case.farm.usePreset', { name: preset.name })}
            </Button>
          ))}
        </div>
        <Form {...form}>
          <form className="case-form" onSubmit={form.handleSubmit(onSubmit)} noValidate>
            <FormField
              control={form.control}
              name="acreage"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farm.acreage')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="decimal" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="production_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farm.productionType')}</FormLabel>
                  <FormControl>
                    <select {...field} className="case-select">
                      <option value="">{t('common.select')}</option>
                      {PRODUCTION_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {presetLabel(type, t)}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="latitude"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farm.latitude')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="decimal" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="longitude"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farm.longitude')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="decimal" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <MutationAlert
              message={error}
              onRetry={
                lastBody.current
                  ? () => {
                      void send(lastBody.current as FarmRouteCreate);
                    }
                  : undefined
              }
            />
            <PendingButton type="submit" pending={pending}>
              {t('case.farm.create')}
            </PendingButton>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
