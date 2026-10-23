import { describe, expect, it } from 'vitest';
import { buildFlow } from './flows';
import { buildResponse, currentStep, startUssd, ussdReducer, type UssdState } from './machine';

function press(state: UssdState, ...keys: string[]): UssdState {
  return keys.reduce((current, key) => ussdReducer(current, { type: 'press', key }), state);
}

describe('USSD machine', () => {
  it('ends the community flow immediately when the verifier does not know the farmer', () => {
    const flow = buildFlow('trust_source', 'Kariuki Mwangi');
    const state = press(startUssd(flow), '2');

    expect(state.complete).toBe(true);
    expect(buildResponse(state)).toEqual({
      participant_type: 'trust_source',
      rating: null,
      comments: null,
      personal_knowledge_flag: false,
    });
  });

  it('collects a 4-point rating from a verifier who knows the farmer', () => {
    const flow = buildFlow('trust_source', 'Kariuki Mwangi');
    expect(startUssd(flow).flow.steps[0]?.prompt).toContain('Kariuki');
    expect(buildResponse(startUssd(flow))).toBeNull();

    const state = press(startUssd(flow), '1', '4', '1');

    expect(state.complete).toBe(true);
    expect(buildResponse(state)).toEqual({
      participant_type: 'trust_source',
      rating: 4,
      comments: null,
      personal_knowledge_flag: true,
    });
  });

  it('maps the buyer answers onto the strict market actor payload', () => {
    const flow = buildFlow('market_actor', 'Nakuru Grain');
    const state = press(startUssd(flow), '4', '2', '3', '4');

    expect(buildResponse(state)).toEqual({
      participant_type: 'market_actor',
      reliability_rating: 4,
      purchase_frequency: 'monthly',
      relationship_months: 18,
      avg_volume_kg: 800,
    });
  });

  it('maps group cycles and a deterministic contribution month', () => {
    const flow = buildFlow('social_group', 'Mwangaza SACCO', new Date('2026-10-19T00:00:00Z'));
    const state = press(startUssd(flow), '4', '1', '3');

    expect(buildResponse(state)).toEqual({
      participant_type: 'social_group',
      consecutive_cycles: 6,
      last_contribution_date: '2026-10-01',
      contribution_amount: 1000,
    });
  });

  it('back removes the answer and re-asks the previous step', () => {
    const flow = buildFlow('market_actor', 'Nakuru Grain');
    const answered = press(startUssd(flow), '1');
    expect(answered.index).toBe(1);

    const back = ussdReducer(answered, { type: 'back' });

    expect(back.index).toBe(0);
    expect(back.answers).toEqual({});
    expect(currentStep(back)?.id).toBe('reliability');
    expect(buildResponse(press(back, '2', '1', '1', '1'))).toMatchObject({
      reliability_rating: 2,
    });
  });

  it('ignores a key that is not on the current screen', () => {
    const flow = buildFlow('trust_source', 'Kariuki');
    const state = startUssd(flow);

    expect(ussdReducer(state, { type: 'press', key: '9' })).toBe(state);
  });
});
