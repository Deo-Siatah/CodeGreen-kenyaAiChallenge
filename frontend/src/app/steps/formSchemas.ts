import { z } from 'zod';
import type {
  FarmerRouteCreate,
  LoanCreate,
  MarketActorCreate,
  SocialGroupCreate,
  TrustSourceCreate,
} from '@/api/schemas';
import { makeTranslator, type Translator } from '@/i18n/dictionary';

const english = makeTranslator('en');

function emptyToNull(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function createFarmerFormSchema(t: Translator = english) {
  return z.object({
    full_name: z.string().min(1, t('validation.required.fullName')),
    national_id: z.string().min(1, t('validation.required.nationalId')),
    phone: z.string().min(1, t('validation.required.phone')),
    gender: z.string().min(1, t('validation.required.gender')),
    date_of_birth: z.string().optional(),
    location: z.string().min(1, t('validation.required.location')),
    village: z.string().optional(),
    sub_county: z.string().optional(),
    county: z.string().optional(),
    farming_type: z.string().optional(),
    years_farming: z.string().optional(),
  });
}

export const farmerFormSchema = createFarmerFormSchema();

export type FarmerFormValues = z.infer<typeof farmerFormSchema>;

export function toFarmerBody(values: FarmerFormValues): FarmerRouteCreate {
  const years = values.years_farming?.trim();
  return {
    full_name: values.full_name.trim(),
    national_id: values.national_id.trim(),
    phone: values.phone.trim(),
    gender: values.gender,
    date_of_birth: emptyToNull(values.date_of_birth),
    location: values.location.trim(),
    village: emptyToNull(values.village),
    sub_county: emptyToNull(values.sub_county),
    county: emptyToNull(values.county),
    farming_type: emptyToNull(values.farming_type),
    years_farming: years ? Number(years) : null,
  };
}

export function createFarmFormSchema(t: Translator = english) {
  return z.object({
    acreage: z
      .string()
      .min(1, t('validation.required.acreage'))
      .refine((value) => Number.isFinite(Number(value)) && Number(value) > 0, {
        message: t('validation.acreage.positive'),
      }),
    production_type: z.string().min(1, t('validation.required.productionType')),
    latitude: z
      .string()
      .min(1, t('validation.required.latitude'))
      .refine(
        (value) => {
          const n = Number(value);
          return Number.isFinite(n) && n >= -90 && n <= 90;
        },
        { message: t('validation.latitude.range') },
      ),
    longitude: z
      .string()
      .min(1, t('validation.required.longitude'))
      .refine(
        (value) => {
          const n = Number(value);
          return Number.isFinite(n) && n >= -180 && n <= 180;
        },
        { message: t('validation.longitude.range') },
      ),
  });
}

export const farmFormSchema = createFarmFormSchema();

export type FarmFormValues = z.infer<typeof farmFormSchema>;

export function toFarmBody(values: FarmFormValues): {
  acreage: number;
  production_type: string | null;
  latitude: number;
  longitude: number;
} {
  return {
    acreage: Number(values.acreage),
    production_type: values.production_type || null,
    latitude: Number(values.latitude),
    longitude: Number(values.longitude),
  };
}

export function createTrustSourceFormSchema(t: Translator = english) {
  return z.object({
    name: z.string().min(1, t('validation.required.name')),
    category: z.string().min(1, t('validation.required.category')),
    phone: z.string().optional(),
    location: z.string().min(1, t('validation.required.location')),
  });
}

export const trustSourceFormSchema = createTrustSourceFormSchema();

export type TrustSourceFormValues = z.infer<typeof trustSourceFormSchema>;

export function toTrustSourceBody(values: TrustSourceFormValues): TrustSourceCreate {
  return {
    name: values.name.trim(),
    category: values.category,
    phone: emptyToNull(values.phone),
    national_id: null,
    location: values.location.trim(),
  };
}

export function createMarketActorFormSchema(t: Translator = english) {
  return z.object({
    name: z.string().min(1, t('validation.required.name')),
    actor_type: z.string().min(1, t('validation.required.buyerType')),
    phone: z.string().optional(),
    location: z.string().min(1, t('validation.required.location')),
  });
}

export const marketActorFormSchema = createMarketActorFormSchema();

export type MarketActorFormValues = z.infer<typeof marketActorFormSchema>;

export function toMarketActorBody(values: MarketActorFormValues): MarketActorCreate {
  return {
    name: values.name.trim(),
    actor_type: values.actor_type,
    phone: emptyToNull(values.phone),
    location: values.location.trim(),
  };
}

export function createSocialGroupFormSchema(t: Translator = english) {
  return z.object({
    name: z.string().min(1, t('validation.required.name')),
    group_type: z.string().min(1, t('validation.required.groupType')),
    location: z.string().min(1, t('validation.required.location')),
  });
}

export const socialGroupFormSchema = createSocialGroupFormSchema();

export type SocialGroupFormValues = z.infer<typeof socialGroupFormSchema>;

export function toSocialGroupBody(values: SocialGroupFormValues): SocialGroupCreate {
  return {
    name: values.name.trim(),
    group_type: values.group_type,
    location: values.location.trim(),
    formation_year: null,
  };
}

export function createLoanFormSchema(t: Translator = english) {
  return z.object({
    amount: z
      .string()
      .min(1, t('validation.required.loanAmount'))
      .refine((value) => Number.isFinite(Number(value)) && Number(value) > 0, {
        message: t('validation.loanAmount.positive'),
      }),
    purpose: z.string().optional(),
    duration_months: z
      .string()
      .optional()
      .refine(
        (value) => {
          const trimmed = value?.trim();
          if (!trimmed) {
            return true;
          }
          const n = Number(trimmed);
          return Number.isInteger(n) && n > 0;
        },
        { message: t('validation.loanDuration.positive') },
      ),
    interest_rate: z
      .string()
      .optional()
      .refine(
        (value) => {
          const trimmed = value?.trim();
          if (!trimmed) {
            return true;
          }
          const n = Number(trimmed);
          return Number.isFinite(n) && n >= 0;
        },
        { message: t('validation.loanInterest.nonNegative') },
      ),
  });
}

export const loanFormSchema = createLoanFormSchema();

export type LoanFormValues = z.infer<typeof loanFormSchema>;

export function toLoanBody(values: LoanFormValues, farmerId: string): LoanCreate {
  const duration = values.duration_months?.trim();
  const interest = values.interest_rate?.trim();
  return {
    farmer_id: farmerId,
    amount: Number(values.amount),
    purpose: emptyToNull(values.purpose),
    duration_months: duration ? Number(duration) : null,
    interest_rate: interest ? Number(interest) : null,
  };
}

export function firstNameOf(fullName: string): string {
  const [first] = fullName.trim().split(/\s+/);
  return first && first.length > 0 ? first : fullName.trim();
}
