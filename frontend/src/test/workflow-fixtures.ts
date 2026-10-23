import type { FarmerDetailResponse } from '@/api/schemas';

export const API = 'http://localhost:8000';

export const farmerFormValues = {
  full_name: 'Ann Wanjiku',
  national_id: '12345678',
  phone: '0712345678',
  gender: 'Female',
  date_of_birth: '1990-01-01',
  location: 'Nakuru',
  village: '',
  sub_county: '',
  county: 'Nakuru',
  farming_type: 'Crop',
  years_farming: '',
};

export const farmerRequestBody = {
  full_name: 'Ann Wanjiku',
  national_id: '12345678',
  phone: '0712345678',
  gender: 'Female',
  date_of_birth: '1990-01-01',
  location: 'Nakuru',
  village: null,
  sub_county: null,
  county: 'Nakuru',
  farming_type: 'Crop',
  years_farming: null,
};

export const farmerResponse: FarmerDetailResponse = {
  id: 'farmer-1',
  full_name: 'Ann Wanjiku',
  national_id: '12345678',
  phone: '0712345678',
  gender: 'Female',
  date_of_birth: '1990-01-01',
  location: 'Nakuru',
  village: null,
  sub_county: null,
  county: 'Nakuru',
  farming_type: 'Crop',
  years_farming: null,
  created_at: '2026-01-01T00:00:00Z',
};

export const farmRequestBody = {
  acreage: 2.5,
  production_type: 'Crop',
  latitude: -0.3031,
  longitude: 36.08,
};

export const farmResponse = {
  id: 'farm-1',
  farmer_id: 'farmer-1',
  ...farmRequestBody,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

export const trustSourceEntity = {
  id: 'ts-1',
  full_name: 'Kariuki',
  category: 'administrative official',
  phone: '0711111111',
  national_id: null,
  location: 'Nakuru',
  created_at: '2026-01-01T00:00:00Z',
};

export const marketActorEntity = {
  id: 'ma-1',
  name: 'Nakuru Grain',
  actor_type: 'Buyer',
  phone: '0722222222',
  location: 'Nakuru',
  created_at: '2026-01-01T00:00:00Z',
};

export const socialGroupEntity = {
  id: 'sg-1',
  name: 'Mwangaza SACCO',
  group_type: 'SACCO',
  location: 'Nakuru',
  formation_year: null,
  created_at: '2026-01-01T00:00:00Z',
};

export function linkResponse(farmerId: string, field: string, relatedId: string) {
  return {
    farmer_id: farmerId,
    [field]: relatedId,
    relationship_type: 'test',
    created_at: '2026-01-01T00:00:00Z',
  };
}
