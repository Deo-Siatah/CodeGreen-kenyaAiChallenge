export const COMMUNITY_CATEGORIES = [
  'administrative official',
  'family member',
  'neighbour',
  'friend',
] as const;

export const BUYER_TYPES = [
  'Buyer',
  'Aggregator',
  'Agrovet',
  'Processor',
  'Cooperative',
] as const;

export const GROUP_TYPES = [
  'SACCO',
  'Chama',
  'Table Banking',
  'Self Help Group',
] as const;

export const PRODUCTION_TYPES = ['Crop', 'Livestock', 'Mixed'] as const;

export const GENDERS = ['Female', 'Male', 'Other'] as const;

export interface LocationPreset {
  name: string;
  latitude: number;
  longitude: number;
}

export const LOCATION_PRESETS: LocationPreset[] = [
  { name: 'Nakuru', latitude: -0.3031, longitude: 36.08 },
  { name: 'Meru', latitude: 0.05, longitude: 37.65 },
  { name: 'Kitale', latitude: 1.0157, longitude: 35.0062 },
];
