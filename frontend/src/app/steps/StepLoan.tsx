import { useEffect, useMemo, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { LoanResponse } from '@/api/schemas';
import { ApiError } from '@/api/errors';
import {
  createLoan,
  defaultLoan,
  getLoans,
  markDisbursed,
  repayLoan,
} from '@/api/endpoints/loans';
import { Button } from '@/components/ui/button';
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
import { loanStatusLabel } from '@/i18n/labels';
import { formatMoney } from '@/lib/format';
import { useCaseStore } from '../caseStore';
import { MutationAlert, PendingButton } from '../controls';
import {
  createLoanFormSchema,
  toLoanBody,
  type LoanFormValues,
} from './formSchemas';

type LoanAction = 'disburse' | 'repay' | 'default';

function isOpenLoan(loan: LoanResponse): boolean {
  return loan.status === 'pending_disbursement' || loan.status === 'disbursed';
}

export function StepLoan() {
  const { t } = useI18n();
  const caseId = useCaseStore((state) => state.caseId);
  const score = useGraphStore((state) => state.score);
  const dispatch = useGraphStore((state) => state.dispatch);

  const [loans, setLoans] = useState<LoanResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const inFlight = useRef(false);

  const schema = useMemo(() => createLoanFormSchema(t), [t]);
  const form = useForm<LoanFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      amount: '',
      purpose: '',
      duration_months: '',
      interest_rate: '',
    },
  });

  useEffect(() => {
    if (!caseId || caseId === 'new') {
      setLoading(false);
      return;
    }

    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);

    void getLoans({ farmer_id: caseId }, controller.signal)
      .then((data) => {
        if (active) {
          setLoans(data);
        }
      })
      .catch((err: unknown) => {
        if (!active || (err instanceof ApiError && err.kind === 'cancelled')) {
          return;
        }
        setLoadError(err instanceof ApiError ? err.message : t('case.loan.loadError'));
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [caseId, t]);

  const openLoan = loans.find(isOpenLoan) ?? null;
  const recommended = score?.recommendedAmount ?? null;

  async function add(values: LoanFormValues) {
    if (!caseId || caseId === 'new' || inFlight.current) {
      return;
    }
    inFlight.current = true;
    setCreating(true);
    setError(null);
    try {
      const loan = await createLoan(toLoanBody(values, caseId));
      setLoans((current) => [loan, ...current]);
      await dispatch([
        {
          type: 'LOAN_CREATED',
          loanId: loan.id,
          amount: loan.amount,
          label: t('case.loan.title'),
        },
      ]);
      form.reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('case.loan.error.create'));
    } finally {
      inFlight.current = false;
      setCreating(false);
    }
  }

  async function act(loan: LoanResponse, action: LoanAction) {
    if (inFlight.current) {
      return;
    }
    inFlight.current = true;
    setPendingKey(`${loan.id}:${action}`);
    setError(null);
    try {
      const result =
        action === 'disburse'
          ? await markDisbursed(loan.id)
          : action === 'repay'
            ? await repayLoan(loan.id)
            : await defaultLoan(loan.id);

      setLoans((current) =>
        current.map((item) => (item.id === result.id ? result : item)),
      );

      if (action === 'disburse') {
        await dispatch([{ type: 'LOAN_DISBURSED', loanId: result.id }]);
      } else {
        await dispatch([
          {
            type: 'LOAN_RESOLVED',
            loanId: result.id,
            outcome: action === 'repay' ? 'repaid' : 'defaulted',
          },
        ]);
      }
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : action === 'disburse'
            ? t('case.loan.error.disburse')
            : t('case.loan.error.resolve'),
      );
    } finally {
      inFlight.current = false;
      setPendingKey(null);
    }
  }

  return (
    <div className="case-loan">
      <Card className="case-card">
        <CardHeader>
          <CardTitle>{t('case.loan.title')}</CardTitle>
          <CardDescription>{t('case.loan.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          {recommended === null ? (
            <p className="case-status">{t('case.loan.needScore')}</p>
          ) : (
            <p className="loan-recommendation" data-testid="loan-recommendation">
              {t('case.loan.recommendation', { amount: formatMoney(recommended) })}
            </p>
          )}

          {loadError ? <MutationAlert message={loadError} /> : null}

          {loading ? <p className="case-status">{t('case.loan.loading')}</p> : null}

          {!loading && !openLoan && recommended !== null ? (
            <Form {...form}>
              <form
                className="case-form"
                onSubmit={form.handleSubmit((values) => void add(values))}
              >
                <FormField
                  control={form.control}
                  name="amount"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('case.loan.amount')}</FormLabel>
                      <FormControl>
                        <Input
                          {...field}
                          inputMode="decimal"
                          placeholder={formatMoney(recommended)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="purpose"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('case.loan.purpose')}</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="loan-form__row">
                  <FormField
                    control={form.control}
                    name="duration_months"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('case.loan.duration')}</FormLabel>
                        <FormControl>
                          <Input {...field} inputMode="numeric" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="interest_rate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('case.loan.interest')}</FormLabel>
                        <FormControl>
                          <Input {...field} inputMode="decimal" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <PendingButton type="submit" pending={creating}>
                  {t('case.loan.create')}
                </PendingButton>
              </form>
            </Form>
          ) : null}

          <MutationAlert message={error} />
        </CardContent>
      </Card>

      <Card className="case-card">
        <CardHeader>
          <CardTitle>{t('case.loan.history')}</CardTitle>
        </CardHeader>
        <CardContent>
          {!loading && loans.length === 0 ? (
            <p className="case-status">{t('case.loan.empty')}</p>
          ) : null}

          <ul className="loan-list">
            {loans.map((loan) => {
              const disburseKey = `${loan.id}:disburse`;
              const repayKey = `${loan.id}:repay`;

              return (
                <li
                  key={loan.id}
                  className="loan-row"
                  data-testid="loan-row"
                  aria-label={t('case.loan.rowAria', { amount: formatMoney(loan.amount) })}
                >
                  <div className="loan-row__summary">
                    <span className="loan-row__amount">KES {formatMoney(loan.amount)}</span>
                    <span className="loan-row__status" data-status={loan.status}>
                      {loanStatusLabel(loan.status, t)}
                    </span>
                  </div>
                  <p className="loan-row__details">
                    {[
                      loan.purpose,
                      loan.duration_months
                        ? t('case.loan.months', { count: loan.duration_months })
                        : null,
                      loan.interest_rate !== null
                        ? t('case.loan.rate', { rate: loan.interest_rate })
                        : null,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                  <div className="loan-row__actions">
                    {loan.status === 'pending_disbursement' ? (
                      <PendingButton
                        type="button"
                        size="sm"
                        pending={pendingKey === disburseKey}
                        disabled={pendingKey !== null}
                        onClick={() => void act(loan, 'disburse')}
                      >
                        {t('case.loan.disburse')}
                      </PendingButton>
                    ) : null}
                    {loan.status === 'disbursed' ? (
                      <>
                        <PendingButton
                          type="button"
                          size="sm"
                          pending={pendingKey === repayKey}
                          disabled={pendingKey !== null}
                          onClick={() => void act(loan, 'repay')}
                        >
                          {t('case.loan.repay')}
                        </PendingButton>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          disabled={pendingKey !== null}
                          onClick={() => void act(loan, 'default')}
                        >
                          {t('case.loan.default')}
                        </Button>
                      </>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
