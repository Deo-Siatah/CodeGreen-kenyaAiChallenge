import { client } from '../client';
import {
  schemas,
  type MarketActorResponse,
  type SocialGroupResponse,
  type TrustSourceResponse,
  type VerificationStartRequest,
} from '../schemas';
import { validate } from '../validate';

export async function startVerification(
  data: VerificationStartRequest,
  signal?: AbortSignal,
) {
  const body = schemas.VerificationStartRequest.parse(data);
  const response = await client.post('/api/verify/start', body, { signal });
  return validate(schemas.VerificationStartResponse, response.data);
}

export async function getVerificationStatus(sessionId: string, signal?: AbortSignal) {
  const response = await client.get(`/api/verify/${sessionId}/status`, { signal });
  return validate(schemas.VerificationStatusResponse, response.data);
}

export async function submitTrustSourceResponse(
  sessionId: string,
  participantId: string,
  data: TrustSourceResponse,
  signal?: AbortSignal,
) {
  const body = schemas.TrustSourceResponse.parse(data);
  const response = await client.post(
    `/api/verify/${sessionId}/respond/${participantId}`,
    body,
    { signal },
  );
  return validate(schemas.VerificationSubmitResponse, response.data);
}

export async function submitMarketActorResponse(
  sessionId: string,
  participantId: string,
  data: MarketActorResponse,
  signal?: AbortSignal,
) {
  const body = schemas.MarketActorResponse.parse(data);
  const response = await client.post(
    `/api/verify/${sessionId}/respond/${participantId}`,
    body,
    { signal },
  );
  return validate(schemas.VerificationSubmitResponse, response.data);
}

export async function submitSocialGroupResponse(
  sessionId: string,
  participantId: string,
  data: SocialGroupResponse,
  signal?: AbortSignal,
) {
  const body = schemas.SocialGroupResponse.parse(data);
  const response = await client.post(
    `/api/verify/${sessionId}/respond/${participantId}`,
    body,
    { signal },
  );
  return validate(schemas.VerificationSubmitResponse, response.data);
}

export async function timeoutParticipant(
  sessionId: string,
  participantId: string,
  signal?: AbortSignal,
) {
  const response = await client.post(
    `/api/verify/${sessionId}/timeout/${participantId}`,
    undefined,
    { signal },
  );
  return validate(schemas.VerificationTimeoutResponse, response.data);
}

export async function getVerificationResult(sessionId: string, signal?: AbortSignal) {
  const response = await client.get(`/api/verify/${sessionId}/result`, { signal });
  return validate(schemas.VerificationResultResponse, response.data);
}

export async function getVerificationBreakdown(sessionId: string, signal?: AbortSignal) {
  const response = await client.get(`/api/verify/${sessionId}/breakdown`, { signal });
  return validate(schemas.BreakdownResponse, response.data);
}

export async function getExplanation(
  sessionId: string,
  options?: {
    mode?: 'farmer' | 'expert';
    language?: string;
  },
  signal?: AbortSignal,
) {
  const params = new URLSearchParams();
  if (options?.mode) params.append('mode', options.mode);
  if (options?.language) params.append('language', options.language);

  const response = await client.get(`/api/verify/${sessionId}/explanation`, {
    params,
    timeout: 120000,
    signal,
  });
  return validate(schemas.ExplanationResponse, response.data);
}
