import { client } from '../client';
import { schemas, type LoanCreate, type LoanResponse } from '../schemas';
import { validate } from '../validate';

export async function createLoan(data: LoanCreate, signal?: AbortSignal): Promise<LoanResponse> {
  const response = await client.post('/api/loans', data, { signal });
  return validate(schemas.LoanResponse, response.data);
}

export async function markDisbursed(loanId: string, signal?: AbortSignal): Promise<LoanResponse> {
  const response = await client.post(`/api/loans/${loanId}/disburse`, undefined, { signal });
  return validate(schemas.LoanResponse, response.data);
}

export async function repayLoan(loanId: string, signal?: AbortSignal): Promise<LoanResponse> {
  const response = await client.post(`/api/loans/${loanId}/repay`, undefined, { signal });
  return validate(schemas.LoanResponse, response.data);
}

export async function defaultLoan(loanId: string, signal?: AbortSignal): Promise<LoanResponse> {
  const response = await client.post(`/api/loans/${loanId}/default`, undefined, { signal });
  return validate(schemas.LoanResponse, response.data);
}

export async function getLoans(
  params?: {
    farmer_id?: string;
    status?: string;
  },
  signal?: AbortSignal,
): Promise<LoanResponse[]> {
  const response = await client.get('/api/loans', { params, signal });
  return validate(schemas.LoanResponse.array(), response.data);
}
