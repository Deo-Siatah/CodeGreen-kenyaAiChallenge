import { useCallback, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ApiError } from '@/api/errors';
import {
  createMarketActor,
  createSocialGroup,
  createTrustSource,
  linkMarketActor,
  linkSocialGroup,
  linkTrustSource,
} from '@/api/endpoints/trust';
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
import { useCaseStore } from '../caseStore';
import { MutationAlert, PendingButton } from '../controls';
import { BUYER_TYPES, COMMUNITY_CATEGORIES, GROUP_TYPES } from '../presets';
import {
  createMarketActorFormSchema,
  createSocialGroupFormSchema,
  createTrustSourceFormSchema,
  firstNameOf,
  toMarketActorBody,
  toSocialGroupBody,
  toTrustSourceBody,
  type MarketActorFormValues,
  type SocialGroupFormValues,
  type TrustSourceFormValues,
} from './formSchemas';

function useAddVerifier<T>(run: (body: T) => Promise<void>) {
  const { t } = useI18n();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const last = useRef<T | null>(null);
  const inFlight = useRef(false);

  const send = useCallback(
    async (body: T) => {
      if (inFlight.current) {
        return;
      }
      inFlight.current = true;
      setPending(true);
      setError(null);
      try {
        await run(body);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : t('common.unexpectedError'));
      } finally {
        inFlight.current = false;
        setPending(false);
      }
    },
    [run, t],
  );

  return {
    pending,
    error,
    submit: (body: T) => {
      last.current = body;
      void send(body);
    },
    retry: () => {
      if (last.current !== null) {
        void send(last.current);
      }
    },
    canRetry: last.current !== null,
  };
}

function CommunityCard() {
  const { t } = useI18n();
  const caseId = useCaseStore((state) => state.caseId);
  const dispatch = useGraphStore((state) => state.dispatch);

  const schema = useMemo(() => createTrustSourceFormSchema(t), [t]);

  const form = useForm<TrustSourceFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', category: '', phone: '', location: '' },
  });

  const add = useAddVerifier<TrustSourceFormValues>(async (values) => {
    if (!caseId) {
      throw new Error('No case');
    }
    const entity = await createTrustSource(toTrustSourceBody(values));
    await linkTrustSource(caseId, { related_id: entity.id });
    await dispatch([
      { type: 'VERIFIER_ADDED', verifierId: entity.id, kind: 'trust_source', label: firstNameOf(entity.full_name) },
      { type: 'VERIFIER_LINKED', farmerId: caseId, verifierId: entity.id, kind: 'trust_source' },
    ]);
    form.reset();
  });

  return (
    <Card className="case-card">
      <CardHeader>
        <CardTitle>{t('case.network.communityTitle')}</CardTitle>
        <CardDescription>{t('case.network.communityDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form
            className="case-form"
            onSubmit={form.handleSubmit((values) => add.submit(values))}
            noValidate
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.network.communityName')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
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
                  <FormLabel>{t('case.network.communityPhone')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="tel" />
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
                  <FormLabel>{t('case.network.communityLocation')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="category"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.network.category')}</FormLabel>
                  <FormControl>
                    <select {...field} className="case-select">
                      <option value="">{t('common.select')}</option>
                      {COMMUNITY_CATEGORIES.map((category) => (
                        <option key={category} value={category}>
                          {presetLabel(category, t)}
                        </option>
                      ))}
                    </select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <MutationAlert message={add.error} onRetry={add.canRetry ? add.retry : undefined} />
            <PendingButton type="submit" pending={add.pending}>
              {t('case.network.addCommunity')}
            </PendingButton>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function BuyerCard() {
  const { t } = useI18n();
  const caseId = useCaseStore((state) => state.caseId);
  const dispatch = useGraphStore((state) => state.dispatch);

  const schema = useMemo(() => createMarketActorFormSchema(t), [t]);

  const form = useForm<MarketActorFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', actor_type: '', phone: '', location: '' },
  });

  const add = useAddVerifier<MarketActorFormValues>(async (values) => {
    if (!caseId) {
      throw new Error('No case');
    }
    const entity = await createMarketActor(toMarketActorBody(values));
    await linkMarketActor(caseId, { related_id: entity.id });
    await dispatch([
      { type: 'VERIFIER_ADDED', verifierId: entity.id, kind: 'market_actor', label: firstNameOf(entity.name) },
      { type: 'VERIFIER_LINKED', farmerId: caseId, verifierId: entity.id, kind: 'market_actor' },
    ]);
    form.reset();
  });

  return (
    <Card className="case-card">
      <CardHeader>
        <CardTitle>{t('case.network.buyerTitle')}</CardTitle>
        <CardDescription>{t('case.network.buyerDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form
            className="case-form"
            onSubmit={form.handleSubmit((values) => add.submit(values))}
            noValidate
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.network.buyerName')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
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
                  <FormLabel>{t('case.network.buyerPhone')}</FormLabel>
                  <FormControl>
                    <Input {...field} inputMode="tel" />
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
                  <FormLabel>{t('case.network.buyerLocation')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="actor_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.network.buyerType')}</FormLabel>
                  <FormControl>
                    <select {...field} className="case-select">
                      <option value="">{t('common.select')}</option>
                      {BUYER_TYPES.map((type) => (
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
            <MutationAlert message={add.error} onRetry={add.canRetry ? add.retry : undefined} />
            <PendingButton type="submit" pending={add.pending}>
              {t('case.network.addBuyer')}
            </PendingButton>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

function GroupCard() {
  const { t } = useI18n();
  const caseId = useCaseStore((state) => state.caseId);
  const dispatch = useGraphStore((state) => state.dispatch);

  const schema = useMemo(() => createSocialGroupFormSchema(t), [t]);

  const form = useForm<SocialGroupFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', group_type: '', location: '' },
  });

  const add = useAddVerifier<SocialGroupFormValues>(async (values) => {
    if (!caseId) {
      throw new Error('No case');
    }
    const entity = await createSocialGroup(toSocialGroupBody(values));
    await linkSocialGroup(caseId, { related_id: entity.id });
    await dispatch([
      { type: 'VERIFIER_ADDED', verifierId: entity.id, kind: 'social_group', label: firstNameOf(entity.name) },
      { type: 'VERIFIER_LINKED', farmerId: caseId, verifierId: entity.id, kind: 'social_group' },
    ]);
    form.reset();
  });

  return (
    <Card className="case-card">
      <CardHeader>
        <CardTitle>{t('case.network.groupTitle')}</CardTitle>
        <CardDescription>{t('case.network.groupDescription')}</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form
            className="case-form"
            onSubmit={form.handleSubmit((values) => add.submit(values))}
            noValidate
          >
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.network.groupName')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
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
                  <FormLabel>{t('case.network.groupLocation')}</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="group_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('case.network.groupType')}</FormLabel>
                  <FormControl>
                    <select {...field} className="case-select">
                      <option value="">{t('common.select')}</option>
                      {GROUP_TYPES.map((type) => (
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
            <MutationAlert message={add.error} onRetry={add.canRetry ? add.retry : undefined} />
            <PendingButton type="submit" pending={add.pending}>
              {t('case.network.addGroup')}
            </PendingButton>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

export function StepNetwork() {
  return (
    <div className="case-network">
      <CommunityCard />
      <BuyerCard />
      <GroupCard />
    </div>
  );
}
