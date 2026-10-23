import { describe, expect, it } from 'vitest';
import { schemas } from './schemas';

describe('schemas', () => {
  describe('request schemas', () => {
    it('should reject extra fields in request schemas', () => {
      const FarmerRouteCreate = schemas.FarmerRouteCreate;
      
      expect(() => 
        FarmerRouteCreate.parse({
          full_name: 'John Doe',
          national_id: '12345678',
          phone: '0712345678',
          gender: 'Male',
          location: 'Nairobi',
          extra_field: 'should not be allowed'
        })
      ).toThrow();
    });

    it('should validate required fields in FarmerRouteCreate', () => {
      const FarmerRouteCreate = schemas.FarmerRouteCreate;
      
      expect(() => 
        FarmerRouteCreate.parse({
          full_name: 'John Doe',
          national_id: '12345678',
          phone: '0712345678',
          gender: 'Male',
          location: 'Nairobi',
          date_of_birth: '1990-01-01',
          village: null,
          sub_county: null,
          county: null,
          farming_type: null,
          years_farming: null
        })
      ).not.toThrow();
    });

    it('should validate TrustSourceCreate strictly', () => {
      const TrustSourceCreate = schemas.TrustSourceCreate;
      
      expect(() => 
        TrustSourceCreate.parse({
          name: 'Test Trust',
          category: 'Community',
          location: 'Nairobi',
          extra_field: 'should not be allowed'
        })
      ).toThrow();
    });

    it('should validate LoanCreate strictly', () => {
      const LoanCreate = schemas.LoanCreate;
      
      expect(() => 
        LoanCreate.parse({
          farmer_id: '123',
          amount: 1000,
          extra_field: 'should not be allowed'
        })
      ).toThrow();
    });
  });

  describe('response schemas', () => {
    it('should allow extra fields in responses', () => {
      const FarmerDetailResponse = schemas.FarmerDetailResponse;
      
      const validResponse = {
        id: '123',
        full_name: 'John Doe',
        national_id: '12345678',
        phone: '0712345678',
        gender: 'Male',
        date_of_birth: '1990-01-01',
        location: 'Nairobi',
        village: 'Village A',
        sub_county: 'Subcounty B',
        county: 'County C',
        farming_type: 'Crop',
        years_farming: 10,
        created_at: '2023-01-01T00:00:00Z',
        extra_field: 'should be allowed'
      };
      
      expect(() => FarmerDetailResponse.parse(validResponse)).not.toThrow();
    });

    it('should validate the farmer list summary projection', () => {
      const list = {
        items: [
          {
            id: '123',
            full_name: 'John Doe',
            county: null,
            created_at: '2023-01-01T00:00:00Z',
            current_score: null,
          },
        ],
        total: 1,
      };

      expect(() => schemas.FarmersListResponse.parse(list)).not.toThrow();
      expect(() =>
        schemas.FarmersListResponse.parse({
          items: [{ id: '123', full_name: 'John Doe', county: null, created_at: 'x' }],
          total: 1,
        }),
      ).toThrow();
    });

    it('should validate VerificationResponsePayload discriminated union', () => {
      const VerificationResponsePayload = schemas.VerificationResponsePayload;
      
      // Test trust source
      expect(() => 
        VerificationResponsePayload.parse({
          participant_type: 'trust_source',
          rating: 3,
          comments: 'Good',
          personal_knowledge_flag: true
        })
      ).not.toThrow();
      
      // Test market actor
      expect(() => 
        VerificationResponsePayload.parse({
          participant_type: 'market_actor',
          reliability_rating: 4,
          purchase_frequency: 'monthly',
          relationship_months: 12,
          avg_volume_kg: 1000
        })
      ).not.toThrow();
      
      // Test social group
      expect(() => 
        VerificationResponsePayload.parse({
          participant_type: 'social_group',
          consecutive_cycles: 5,
          last_contribution_date: '2023-01-01',
          contribution_amount: 1000
        })
      ).not.toThrow();
    });
  });
});