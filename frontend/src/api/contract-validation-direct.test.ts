import { describe, expect, it } from 'vitest';
import { schemas } from './schemas';

describe('Contract Validation Direct Tests', () => {
  it('should validate farmer response correctly', () => {
    const validFarmer = {
      id: '123',
      full_name: 'John Doe',
      national_id: '12345678',
      phone: '0712345678',
      gender: 'Male',
      date_of_birth: '1990-01-01',
      location: 'Nairobi',
      village: null,
      sub_county: null,
      county: null,
      farming_type: null,
      years_farming: null,
      created_at: '2023-01-01T00:00:00Z'
    };
    
    expect(() => schemas.FarmerDetailResponse.parse(validFarmer)).not.toThrow();
  });

  it('should detect invalid farmer response', () => {
    const invalidFarmer = {
      id: '123',
      full_name: 'John Doe',
      // Missing required field
      national_id: undefined,
      phone: '0712345678',
      gender: 'Male',
      date_of_birth: '1990-01-01',
      location: 'Nairobi',
      village: null,
      sub_county: null,
      county: null,
      farming_type: null,
      years_farming: null,
      created_at: '2023-01-01T00:00:00Z'
    };
    
    expect(() => schemas.FarmerDetailResponse.parse(invalidFarmer)).toThrow();
  });

  it('should detect invalid data types', () => {
    const invalidFarmer = {
      id: 123, // Should be string
      full_name: 123, // Should be string
      national_id: '12345678',
      phone: '0712345678',
      gender: 'Male',
      date_of_birth: '1990-01-01',
      location: 'Nairobi',
      village: null,
      sub_county: null,
      county: null,
      farming_type: null,
      years_farming: null,
      created_at: '2023-01-01T00:00:00Z'
    };
    
    expect(() => schemas.FarmerDetailResponse.parse(invalidFarmer)).toThrow();
  });

  it('should allow extra fields in response', () => {
    const farmerWithExtras = {
      id: '123',
      full_name: 'John Doe',
      national_id: '12345678',
      phone: '0712345678',
      gender: 'Male',
      date_of_birth: '1990-01-01',
      location: 'Nairobi',
      village: null,
      sub_county: null,
      county: null,
      farming_type: null,
      years_farming: null,
      created_at: '2023-01-01T00:00:00Z',
      extra_field: 'should be allowed',
      another_extra: { nested: 'value' }
    };
    
    expect(() => schemas.FarmerDetailResponse.parse(farmerWithExtras)).not.toThrow();
  });

  it('should validate loan request correctly', () => {
    const validLoan = {
      farmer_id: '123-456-789',
      amount: 1000,
      purpose: 'Agricultural equipment',
      duration_months: 12,
      interest_rate: 5.5
    };
    
    expect(() => schemas.LoanCreate.parse(validLoan)).not.toThrow();
  });

  it('should detect invalid loan request', () => {
    const invalidLoan = {
      farmer_id: '123-456-789',
      amount: 0, // Invalid amount
      purpose: 'Agricultural equipment',
      duration_months: 12,
      interest_rate: 5.5
    };
    
    expect(() => schemas.LoanCreate.parse(invalidLoan)).toThrow();
  });

  it('should detect invalid loan data types', () => {
    const invalidLoan = {
      farmer_id: '123-456-789',
      amount: '1000', // Should be number
      purpose: 123, // Should be string
      duration_months: '12', // Should be number
      interest_rate: '5.5' // Should be number
    };
    
    expect(() => schemas.LoanCreate.parse(invalidLoan)).toThrow();
  });
});