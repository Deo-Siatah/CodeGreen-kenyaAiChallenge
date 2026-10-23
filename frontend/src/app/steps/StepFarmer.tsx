import { useMemo, useRef, useState, type FormEvent } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '@/api/errors';
import { createFarmer } from '@/api/endpoints/farmers';
import type { FarmerRouteCreate } from '@/api/schemas';
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
import { useGraphStore } from '@/features/graph/store';
import { useI18n } from '@/i18n';
import { presetLabel } from '@/i18n/labels';
import { MutationAlert, PendingButton } from '../controls';
import { GENDERS, PRODUCTION_TYPES } from '../presets';
import {
  createFarmerFormSchema,
  farmerFormSchema,
  firstNameOf,
  toFarmerBody,
  type FarmerFormValues,
} from './formSchemas';

const DEFAULT_VALUES: FarmerFormValues = {
  full_name: '',
  national_id: '',
  phone: '',
  gender: '',
  date_of_birth: '',
  location: '',
  village: '',
  sub_county: '',
  county: '',
  farming_type: '',
  years_farming: '',
};

function isFarmerField(key: string): key is keyof FarmerFormValues {
  return key in farmerFormSchema.shape;
}

export function StepFarmer() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const dispatch = useGraphStore((state) => state.dispatch);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lastBody = useRef<FarmerRouteCreate | null>(null);
  const inFlight = useRef(false);

  const schema = useMemo(() => createFarmerFormSchema(t), [t]);

  const form = useForm<FarmerFormValues>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULT_VALUES,
  });

  async function run(body: FarmerRouteCreate): Promise<void> {
    inFlight.current = true;
    setPending(true);
    setError(null);

    try {
      const farmer = await createFarmer(body);
      await dispatch([
        { type: 'FARMER_CREATED', farmerId: farmer.id, label: firstNameOf(farmer.full_name) },
      ]);
      navigate(`/case/${farmer.id}`);
    } catch (err) {
      if (err instanceof ApiError && err.kind === 'validation' && err.fieldErrors) {
        let mapped = false;
        for (const [field, message] of Object.entries(err.fieldErrors)) {
          if (isFarmerField(field)) {
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

  const handleSubmission = form.handleSubmit(
    (values) => {
      const body = toFarmerBody(values);
      lastBody.current = body;
      void run(body);
    },
    () => {
      inFlight.current = false;
    },
  );

  function onFormSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    void handleSubmission(event);
  }

  return (
    <Card className="case-card">
      <CardHeader>
        <CardTitle>{t('case.farmer.title')}</CardTitle>
        <CardDescription>{t('case.farmer.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form className="case-form" onSubmit={onFormSubmit} noValidate>
            <FormField
              control={form.control}
              name="full_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.fullName')}</FormLabel>
                  <FormControl>
                    <Input {...field} autoComplete="name" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="national_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.nationalId')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="numeric" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="phone"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.phone')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="tel" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="gender"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.gender')}</FormLabel>
                  <FormControl>
                    <select {...field} className="case-select">
                      <option value="">{t('common.select')}</option>
                      {GENDERS.map((gender) => (
                        <option key={gender} value={gender}>
                          {presetLabel(gender, t)}
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
              name="date_of_birth"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.dob')}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder="YYYY-MM-DD" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="location"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.location')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="village"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.village')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="sub_county"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.subCounty')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="county"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.county')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="farming_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.farmingType')}</FormLabel>
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
              name="years_farming"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.farmer.yearsFarming')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="numeric" />
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
                      const body = lastBody.current;
                      if (body && !inFlight.current) {
                        void run(body);
                      }
                    }
                  : undefined
              }
            />
            <PendingButton type="submit" pending={pending}>
              {t('case.farmer.create')}
            </PendingButton>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
