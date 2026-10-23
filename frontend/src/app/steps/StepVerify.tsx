import { useEffect, useMemo, useRef, useState } from 'react';
import type { VerificationResponsePayload, VerificationStatusResponse } from '@/api/schemas';
import { ApiError } from '@/api/errors';
import {
  getVerificationStatus,
  startVerification,
  submitMarketActorResponse,
  submitSocialGroupResponse,
  submitTrustSourceResponse,
  timeoutParticipant,
} from '@/api/endpoints/verification';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { Rating, VerifierKind } from '@/domain/graph';
import { useGraphStore } from '@/features/graph/store';
import { Handset, buildFlow, type UssdFlow } from '@/features/ussd';
import { useI18n } from '@/i18n';
import { sessionStatusLabel, verifierKindLabel } from '@/i18n/labels';
import { useCaseStore } from '../caseStore';
import { MutationAlert, PendingButton } from '../controls';

interface ParticipantRow {
  participantId: string;
  verifierId: string;
  kind: VerifierKind;
  label: string;
  responded: boolean;
  timedOut: boolean;
}

function isVerifierKind(value: string): value is VerifierKind {
  return value === 'trust_source' || value === 'market_actor' || value === 'social_group';
}

function isRating(value: number | null): value is Rating {
  return value === 1 || value === 2 || value === 3 || value === 4;
}

function sessionFinished(status: string): boolean {
  return status === 'completed' || status === 'insufficient_data';
}

export function StepVerify() {
  const { t, language } = useI18n();
  const caseId = useCaseStore((state) => state.caseId);
  const setStep = useCaseStore((state) => state.setStep);
  const sessionId = useGraphStore((state) => state.sessionId);
  const participants = useGraphStore((state) => state.participants);
  const nodes = useGraphStore((state) => state.nodes);
  const dispatch = useGraphStore((state) => state.dispatch);

  const [sessionStatus, setSessionStatus] = useState<string>('unknown');
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [handsetError, setHandsetError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const inFlight = useRef(false);

  const rows = useMemo<ParticipantRow[]>(() => {
    const result: ParticipantRow[] = [];
    for (const [participantId, verifierId] of Object.entries(participants)) {
      const node = nodes[verifierId];
      if (!node || !isVerifierKind(node.kind)) {
        continue;
      }
      result.push({
        participantId,
        verifierId,
        kind: node.kind,
        label: node.label,
        responded: node.state === 'responded',
        timedOut: node.state === 'timed_out',
      });
    }
    return result;
  }, [participants, nodes]);

  useEffect(() => {
    if (!sessionId) {
      return;
    }
    const controller = new AbortController();
    void getVerificationStatus(sessionId, controller.signal)
      .then((status) => setSessionStatus(status.status))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.kind === 'cancelled') {
          return;
        }
        setError(err instanceof ApiError ? err.message : t('case.verify.error.status'));
      });
    return () => controller.abort();
  }, [sessionId, t]);

  const verifierCount = useMemo(
    () => Object.values(nodes).filter((node) => isVerifierKind(node.kind)).length,
    [nodes],
  );

  const active = rows.find((row) => row.participantId === activeId) ?? null;
  const flow: UssdFlow | null = active
    ? buildFlow(active.kind, active.label, new Date(), language)
    : null;

  async function start() {
    if (inFlight.current || !caseId || caseId === 'new') {
      return;
    }
    inFlight.current = true;
    setStarting(true);
    setError(null);
    try {
      const started = await startVerification({ farmer_id: caseId });
      const status: VerificationStatusResponse = await getVerificationStatus(started.session_id);
      setSessionStatus(status.status);
      await dispatch([
        {
          type: 'SESSION_STARTED',
          sessionId: started.session_id,
          participants: status.participants.map((participant) => ({
            participantId: participant.id,
            verifierId: participant.participant_id,
          })),
        },
      ]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('case.verify.error.start'));
    } finally {
      inFlight.current = false;
      setStarting(false);
    }
  }

  async function send(row: ParticipantRow, response: VerificationResponsePayload) {
    if (inFlight.current || !sessionId) {
      return;
    }
    inFlight.current = true;
    setPendingId(row.participantId);
    setHandsetError(null);
    try {
      const result =
        response.participant_type === 'trust_source'
          ? await submitTrustSourceResponse(sessionId, row.participantId, response)
          : response.participant_type === 'market_actor'
            ? await submitMarketActorResponse(sessionId, row.participantId, response)
            : await submitSocialGroupResponse(sessionId, row.participantId, response);

      await dispatch([
        {
          type: 'PARTICIPANT_RESPONDED',
          participantId: row.participantId,
          rating:
            response.participant_type === 'trust_source' && isRating(response.rating)
              ? response.rating
              : undefined,
        },
      ]);
      setSessionStatus(result.session_status);
      setActiveId(null);
    } catch (err) {
      setHandsetError(err instanceof ApiError ? err.message : t('case.verify.error.answer'));
    } finally {
      inFlight.current = false;
      setPendingId(null);
    }
  }

  async function markNoAnswer(row: ParticipantRow) {
    if (inFlight.current || !sessionId) {
      return;
    }
    inFlight.current = true;
    setPendingId(row.participantId);
    setError(null);
    try {
      const result = await timeoutParticipant(sessionId, row.participantId);
      await dispatch([{ type: 'PARTICIPANT_TIMED_OUT', participantId: row.participantId }]);
      setSessionStatus(result.session_status);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('case.verify.error.timeout'));
    } finally {
      inFlight.current = false;
      setPendingId(null);
    }
  }

  const done = sessionFinished(sessionStatus);

  return (
    <div className="case-verify">
      <Card className="case-card">
        <CardHeader>
          <CardTitle>{t('case.verify.title')}</CardTitle>
          <CardDescription>{t('case.verify.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          {!sessionId ? (
            <div className="case-form">
              <p className="case-status">
                {verifierCount === 0
                  ? t('case.verify.addFirst')
                  : t('case.verify.ready', { count: verifierCount })}
              </p>
              <PendingButton
                type="button"
                pending={starting}
                onClick={() => void start()}
                disabled={verifierCount === 0}
              >
                {t('case.verify.start')}
              </PendingButton>
            </div>
          ) : (
            <>
              <p className="case-status" data-testid="verify-session-status">
                {t('case.verify.round', {
                  status: sessionStatusLabel(sessionStatus, t),
                })}
              </p>
              <ul className="verify-list">
                {rows.map((row) => (
                  <li key={row.participantId} className="verify-row" data-testid="verify-row">
                    <div>
                      <strong>{row.label}</strong>
                      <span className="verify-kind">{verifierKindLabel(row.kind, t)}</span>
                    </div>
                    <div className="verify-actions">
                      {row.responded ? (
                        <span className="verify-state">{t('case.verify.answered')}</span>
                      ) : row.timedOut ? (
                        <span className="verify-state">{t('case.verify.noAnswer')}</span>
                      ) : (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => {
                              setHandsetError(null);
                              setActiveId(row.participantId);
                            }}
                            disabled={pendingId !== null}
                          >
                            {t('case.verify.call', { name: row.label })}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            onClick={() => void markNoAnswer(row)}
                            disabled={pendingId !== null}
                          >
                            {t('case.verify.noAnswer')}
                          </Button>
                        </>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}

          <MutationAlert message={error} />

          {done ? (
            <div className="verify-done">
              <p>
                {sessionStatus === 'completed'
                  ? t('case.verify.complete')
                  : t('case.verify.incomplete')}
              </p>
              <Button type="button" onClick={() => setStep(5)}>
                {t('case.verify.continue')}
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>

      {active && flow ? (
        <Handset
          key={active.participantId}
          flow={flow}
          pending={pendingId === active.participantId}
          error={handsetError}
          onSubmit={(response) => void send(active, response)}
          onCancel={() => setActiveId(null)}
        />
      ) : null}
    </div>
  );
}
