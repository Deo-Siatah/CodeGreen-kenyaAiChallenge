export interface Farmer {
  id: string;
  full_name: string;
  phone: string;
  gender: string;
  age: number;
  location: string;
  farming_type: string;
  status: string;
  registration_date?: string;
  years_farming?: number;
  education_level?: string;
}

export interface ParticipantScore {
  participant_type: string;
  participant_name: string;
  phone: string;
  responses: Array<{ question_id: string; answer: string }>;
  raw_score: number;
  weight: number;
  weighted_score: number;
  status: 'received' | 'pending' | 'timeout';
}

export interface VerificationLog {
  timestamp: string;
  event: string;
  participant?: string;
  phone?: string;
  details: Record<string, any>;
}

export interface FinalResult {
  session_id: string;
  farmer_id: string;
  farmer_name: string;
  status: string;
  created_at: string;
  completed_at?: string;
  trust_score: number;
  decision: 'ELIGIBLE' | 'REVIEW_REQUIRED' | 'DECLINE';
  recommendation: 'APPROVE_LEVEL_1' | 'APPROVE_LEVEL_2' | 'DECLINE' | 'REVIEW';
  loan_amount_recommended_kes?: number;
  participant_scores: ParticipantScore[];
  analysis: {
    summary: string;
    explanation: string;
    key_drivers: string[];
    risk_factors: string[];
  };
}

export interface Testifier {
  id: string;
  name: string;
  category: string;
  credibility_score: number;
  location: string;
  vouched_count: number;
  default_rate: number;
  current_weight: number;
}

const BACKEND_URL = 'http://localhost:8000';

// Mock Data representing the 5 seeded farmers + additional metadata
export const MOCK_FARMERS: Farmer[] = [
  {
    id: 'f1-kamau',
    full_name: 'John Kamau',
    phone: '0712345678',
    gender: 'Male',
    age: 34,
    location: 'Kirinyaga',
    farming_type: 'Banana Farming',
    status: 'active',
    registration_date: '2026-05-10T10:00:00Z',
    years_farming: 8,
    education_level: 'Secondary School'
  },
  {
    id: 'f2-wanjiku',
    full_name: 'Mary Wanjiku',
    phone: '0722334455',
    gender: 'Female',
    age: 41,
    location: 'Nyeri',
    farming_type: 'Dairy Farming',
    status: 'active',
    registration_date: '2026-05-15T11:30:00Z',
    years_farming: 15,
    education_level: 'Primary School'
  },
  {
    id: 'f3-mwangi',
    full_name: 'Peter Mwangi',
    phone: '0733445566',
    gender: 'Male',
    age: 29,
    location: 'Meru',
    farming_type: 'Maize Farming',
    status: 'active',
    registration_date: '2026-06-01T08:45:00Z',
    years_farming: 4,
    education_level: 'Diploma'
  },
  {
    id: 'f4-atieno',
    full_name: 'Grace Atieno',
    phone: '0744556677',
    gender: 'Female',
    age: 38,
    location: 'Kisumu',
    farming_type: 'Poultry Farming',
    status: 'active',
    registration_date: '2026-06-12T14:20:00Z',
    years_farming: 6,
    education_level: 'University'
  },
  {
    id: 'f5-kiptoo',
    full_name: 'James Kiptoo',
    phone: '0755667788',
    gender: 'Male',
    age: 45,
    location: 'Eldoret',
    farming_type: 'Mixed Farming',
    status: 'active',
    registration_date: '2026-06-20T09:15:00Z',
    years_farming: 20,
    education_level: 'None'
  }
];

export const MOCK_TESTIFIERS: Testifier[] = [
  {
    id: 'ts-1',
    name: 'Chief Njoroge',
    category: 'Chief',
    credibility_score: 95,
    location: 'Kirinyaga East',
    vouched_count: 32,
    default_rate: 3.1, // 3.1% default rate among vouched farmers
    current_weight: 4.0
  },
  {
    id: 'ts-2',
    name: 'Mzee Kariuki',
    category: 'Village Elder',
    credibility_score: 88,
    location: 'Nyeri Central',
    vouched_count: 24,
    default_rate: 4.2,
    current_weight: 3.0
  },
  {
    id: 'ts-3',
    name: 'Mr Mutiso',
    category: 'Teacher',
    credibility_score: 85,
    location: 'Nyeri North',
    vouched_count: 15,
    default_rate: 6.7,
    current_weight: 3.0
  },
  {
    id: 'ts-4',
    name: 'Green Agrovet (Kirinyaga)',
    category: 'Agrovet Owner',
    credibility_score: 90,
    location: 'Kirinyaga West',
    vouched_count: 45,
    default_rate: 2.2,
    current_weight: 3.0
  },
  {
    id: 'ts-5',
    name: 'Nurse Atieno',
    category: 'Health Worker',
    credibility_score: 82,
    location: 'Kisumu Central',
    vouched_count: 18,
    default_rate: 11.1, // High default rate -> trust weight should decrease
    current_weight: 2.5
  },
  {
    id: 'ts-6',
    name: 'Aggressive Agrovet (Eldoret)',
    category: 'Agrovet Owner',
    credibility_score: 45, // Bad history
    location: 'Eldoret South',
    vouched_count: 28,
    default_rate: 28.5, // Extremely high default rate -> flagged!
    current_weight: 1.0 // Heavily reduced weight
  }
];

export const MOCK_VERIFICATION_RESULTS: Record<string, FinalResult> = {
  'f1-kamau': {
    session_id: 'sess-f1',
    farmer_id: 'f1-kamau',
    farmer_name: 'John Kamau',
    status: 'complete',
    created_at: '2026-06-27T10:00:00Z',
    completed_at: '2026-06-27T12:00:00Z',
    trust_score: 82.5,
    decision: 'ELIGIBLE',
    recommendation: 'APPROVE_LEVEL_2',
    loan_amount_recommended_kes: 5000,
    participant_scores: [
      {
        participant_type: 'Chief',
        participant_name: 'Chief Njoroge',
        phone: '0711223344',
        status: 'received',
        raw_score: 100,
        weight: 4,
        weighted_score: 400,
        responses: [
          { question_id: 'CH1_TRUST', answer: 'YES' },
          { question_id: 'CH2_RESIDENCE', answer: 'YES' },
          { question_id: 'CH3_FARM_PLAN', answer: 'YES' }
        ]
      },
      {
        participant_type: 'Agrovet Owner',
        participant_name: 'Green Agrovet',
        phone: '0755443322',
        status: 'received',
        raw_score: 66.67,
        weight: 3,
        weighted_score: 200,
        responses: [
          { question_id: 'AG1_CUSTOMER', answer: 'YES' },
          { question_id: 'AG2_REPAYMENT', answer: 'YES' },
          { question_id: 'AG3_REPUTATION', answer: 'NO' }
        ]
      },
      {
        participant_type: 'Buyer',
        participant_name: 'Banana Aggregator',
        phone: '0799887766',
        status: 'received',
        raw_score: 75,
        weight: 4,
        weighted_score: 300,
        responses: [
          { question_id: 'BY1_DELIVERY', answer: 'YES' },
          { question_id: 'BY2_RELIABILITY', answer: 'YES' }
        ]
      }
    ],
    analysis: {
      summary: 'Strong community verification and reliable buyer relationship.',
      explanation: 'The farmer achieved a trust score of 83/100. Chief Njoroge confirmed strong local character and farm viability. Input supplier purchases are consistent, and banana deliveries to the aggregator indicate reliable sales records.',
      key_drivers: [
        'Chief (Chief Njoroge) provided strong positive verification (+100 points)',
        'Banana Aggregator confirmed consistent delivery volumes (+75 points)',
        'Mwea SACCO active member with verified savings'
      ],
      risk_factors: [
        'Agrovet owner indicated some minor delayed input credit settlements in the past.'
      ]
    }
  },
  'f2-wanjiku': {
    session_id: 'sess-f2',
    farmer_id: 'f2-wanjiku',
    farmer_name: 'Mary Wanjiku',
    status: 'complete',
    created_at: '2026-06-27T08:00:00Z',
    completed_at: '2026-06-27T10:45:00Z',
    trust_score: 76.25,
    decision: 'ELIGIBLE',
    recommendation: 'APPROVE_LEVEL_1',
    loan_amount_recommended_kes: 3000,
    participant_scores: [
      {
        participant_type: 'Village Elder',
        participant_name: 'Mzee Kariuki',
        phone: '0722001122',
        status: 'received',
        raw_score: 100,
        weight: 3,
        weighted_score: 300,
        responses: [
          { question_id: 'EL1_KNOW', answer: 'YES' },
          { question_id: 'EL2_CHARACTER', answer: 'YES' }
        ]
      },
      {
        participant_type: 'Teacher',
        participant_name: 'Mr Mutiso',
        phone: '0733112233',
        status: 'received',
        raw_score: 50,
        weight: 3,
        weighted_score: 150,
        responses: [
          { question_id: 'TE1_PAYMENT', answer: 'YES' },
          { question_id: 'TE2_RELIABILITY', answer: 'NO' }
        ]
      },
      {
        participant_type: 'Buyer',
        participant_name: 'Milk Collection Center',
        phone: '0788112233',
        status: 'received',
        raw_score: 75,
        weight: 4,
        weighted_score: 300,
        responses: [
          { question_id: 'BY1_DELIVERY', answer: 'YES' },
          { question_id: 'BY2_RELIABILITY', answer: 'YES' }
        ]
      }
    ],
    analysis: {
      summary: 'Verified farming activity with moderate community trust.',
      explanation: 'The farmer achieved a trust score of 76/100. Village Elder Kariuki verified her local residence and farming type. The cooperative buyer confirmed daily milk delivery, although school fees repayment records showed some historical delays.',
      key_drivers: [
        'Village Elder (Mzee Kariuki) confirmed solid character and agricultural capacity.',
        'Milk Collection Center reported reliable daily milk volume deliveries.'
      ],
      risk_factors: [
        'Local school head indicated some past delayed school fee instalments.'
      ]
    }
  },
  'f3-mwangi': {
    session_id: 'sess-f3',
    farmer_id: 'f3-mwangi',
    farmer_name: 'Peter Mwangi',
    status: 'complete',
    created_at: '2026-06-26T09:00:00Z',
    completed_at: '2026-06-26T15:00:00Z',
    trust_score: 61.4,
    decision: 'ELIGIBLE',
    recommendation: 'APPROVE_LEVEL_1',
    loan_amount_recommended_kes: 3000,
    participant_scores: [
      {
        participant_type: 'Chief',
        participant_name: 'Chief Njoroge',
        phone: '0711223344',
        status: 'received',
        raw_score: 50,
        weight: 4,
        weighted_score: 200,
        responses: [
          { question_id: 'CH1_TRUST', answer: 'YES' },
          { question_id: 'CH2_RESIDENCE', answer: 'NO' },
          { question_id: 'CH3_FARM_PLAN', answer: 'UNSURE' }
        ]
      },
      {
        participant_type: 'Buyer',
        participant_name: 'Produce Trader',
        phone: '0744112233',
        status: 'received',
        raw_score: 75,
        weight: 3,
        weighted_score: 225,
        responses: [
          { question_id: 'BY1_DELIVERY', answer: 'YES' },
          { question_id: 'BY2_RELIABILITY', answer: 'YES' }
        ]
      }
    ],
    analysis: {
      summary: 'Marginal community trust; review recommended before level upgrades.',
      explanation: 'The farmer achieved a trust score of 61/100, which qualifies for Level 1 credit conditionally. The chief had mixed responses due to the farmer being a young relative newcomer, but the buyer confirmed Maize trades are active.',
      key_drivers: [
        'Maize trader confirmed regular seasonal sales transactions (+75 points).'
      ],
      risk_factors: [
        'Chief reported uncertainty regarding the farmer\'s permanent residence and farm planning.'
      ]
    }
  },
  'f4-atieno': {
    session_id: 'sess-f4',
    farmer_id: 'f4-atieno',
    farmer_name: 'Grace Atieno',
    status: 'pending',
    created_at: '2026-06-27T11:00:00Z',
    trust_score: 45.0,
    decision: 'REVIEW_REQUIRED',
    recommendation: 'REVIEW',
    loan_amount_recommended_kes: undefined,
    participant_scores: [
      {
        participant_type: 'Chief',
        participant_name: 'Chief Njoroge',
        phone: '0711223344',
        status: 'pending',
        raw_score: 0,
        weight: 4,
        weighted_score: 0,
        responses: []
      },
      {
        participant_type: 'Health Worker',
        participant_name: 'Nurse Atieno',
        phone: '0766112233',
        status: 'received',
        raw_score: 100,
        weight: 3,
        weighted_score: 300,
        responses: [
          { question_id: 'HW1_KNOW', answer: 'YES' },
          { question_id: 'HW2_REPUTATION', answer: 'YES' }
        ]
      }
    ],
    analysis: {
      summary: 'Verification in progress. Awaiting chief testimony.',
      explanation: 'The current trust score is 43/100. Verification is pending responses from Chief Njoroge. Nurse Atieno provided a positive endorsement.',
      key_drivers: [
        'Health worker (Nurse Atieno) provided positive local testimony.'
      ],
      risk_factors: [
        'Awaiting Chief Njoroge response (pending since 5 hours ago).'
      ]
    }
  },
  'f5-kiptoo': {
    session_id: 'sess-f5',
    farmer_id: 'f5-kiptoo',
    farmer_name: 'James Kiptoo',
    status: 'timeout',
    created_at: '2026-06-24T09:00:00Z',
    completed_at: '2026-06-26T09:00:00Z',
    trust_score: 33.33,
    decision: 'DECLINE',
    recommendation: 'DECLINE',
    loan_amount_recommended_kes: undefined,
    participant_scores: [
      {
        participant_type: 'Agrovet Owner',
        participant_name: 'Aggressive Agrovet',
        phone: '0799001122',
        status: 'received',
        raw_score: 100,
        weight: 1, // Credibility penalty reduced weight to 1
        weighted_score: 100,
        responses: [
          { question_id: 'AG1_CUSTOMER', answer: 'YES' },
          { question_id: 'AG2_REPAYMENT', answer: 'YES' }
        ]
      },
      {
        participant_type: 'Chief',
        participant_name: 'Chief Njoroge',
        phone: '0711223344',
        status: 'timeout',
        raw_score: 0,
        weight: 4,
        weighted_score: 0,
        responses: []
      }
    ],
    analysis: {
      summary: 'Insufficient community trust due to key verifier non-response.',
      explanation: 'The farmer achieved a trust score of 33/100. Chief Njoroge did not respond within the 48-hour window, heavily penalizing the overall score. The only response came from an agrovet that has been flagged with reduced credibility weight.',
      key_drivers: [
        'Agrovet vouching was recorded, but has a heavily discounted weight (1x).'
      ],
      risk_factors: [
        'Chief did not respond within 48h, penalizing score to 0 for this node.',
        'Verifier (Aggressive Agrovet) has an elevated default rate history (28.5%).'
      ]
    }
  }
};

export const MOCK_VERIFICATION_LOGS: Record<string, VerificationLog[]> = {
  'f1-kamau': [
    { timestamp: '2026-06-27T10:00:00Z', event: 'VERIFICATION_STARTED', details: { farmer_name: 'John Kamau' } },
    { timestamp: '2026-06-27T10:05:00Z', event: 'PARTICIPANT_CONTACTED', participant: 'Chief', phone: '0711223344', details: {} },
    { timestamp: '2026-06-27T10:06:00Z', event: 'PARTICIPANT_CONTACTED', participant: 'Agrovet Owner', phone: '0755443322', details: {} },
    { timestamp: '2026-06-27T10:07:00Z', event: 'PARTICIPANT_CONTACTED', participant: 'Buyer', phone: '0799887766', details: {} },
    { timestamp: '2026-06-27T10:30:00Z', event: 'RESPONSE_RECEIVED', participant: 'Chief', phone: '0711223344', details: { question_id: 'CH1_TRUST', answer: 'YES' } },
    { timestamp: '2026-06-27T10:32:00Z', event: 'RESPONSE_RECEIVED', participant: 'Chief', phone: '0711223344', details: { question_id: 'CH2_RESIDENCE', answer: 'YES' } },
    { timestamp: '2026-06-27T10:35:00Z', event: 'RESPONSE_RECEIVED', participant: 'Chief', phone: '0711223344', details: { question_id: 'CH3_FARM_PLAN', answer: 'YES' } },
    { timestamp: '2026-06-27T10:35:00Z', event: 'PARTICIPANT_COMPLETE', participant: 'Chief', phone: '0711223344', details: {} },
    { timestamp: '2026-06-27T11:15:00Z', event: 'RESPONSE_RECEIVED', participant: 'Buyer', phone: '0799887766', details: { question_id: 'BY1_DELIVERY', answer: 'YES' } },
    { timestamp: '2026-06-27T11:17:00Z', event: 'RESPONSE_RECEIVED', participant: 'Buyer', phone: '0799887766', details: { question_id: 'BY2_RELIABILITY', answer: 'YES' } },
    { timestamp: '2026-06-27T11:17:00Z', event: 'PARTICIPANT_COMPLETE', participant: 'Buyer', phone: '0799887766', details: {} },
    { timestamp: '2026-06-27T11:50:00Z', event: 'RESPONSE_RECEIVED', participant: 'Agrovet Owner', phone: '0755443322', details: { question_id: 'AG1_CUSTOMER', answer: 'YES' } },
    { timestamp: '2026-06-27T11:51:00Z', event: 'RESPONSE_RECEIVED', participant: 'Agrovet Owner', phone: '0755443322', details: { question_id: 'AG2_REPAYMENT', answer: 'YES' } },
    { timestamp: '2026-06-27T11:53:00Z', event: 'RESPONSE_RECEIVED', participant: 'Agrovet Owner', phone: '0755443322', details: { question_id: 'AG3_REPUTATION', answer: 'NO' } },
    { timestamp: '2026-06-27T11:53:00Z', event: 'PARTICIPANT_COMPLETE', participant: 'Agrovet Owner', phone: '0755443322', details: {} },
    { timestamp: '2026-06-27T12:00:00Z', event: 'VERIFICATION_COMPLETE', details: { trust_score: 82.5, decision: 'ELIGIBLE' } }
  ]
};

// API Class with fallback to mock data
export class ApiService {
  private useMock: boolean = false;

  constructor() {
    // Detect if we should use mock data based on local storage or auto fallback
    const saved = localStorage.getItem('hifadhi_use_mock');
    this.useMock = saved === 'true' || saved === null; // Default to mock for robust presentations
  }

  setMockMode(enable: boolean) {
    this.useMock = enable;
    localStorage.setItem('hifadhi_use_mock', String(enable));
  }

  isMockMode(): boolean {
    return this.useMock;
  }

  async testConnection(): Promise<boolean> {
    try {
      const res = await fetch(`${BACKEND_URL}/farmers`, { signal: AbortSignal.timeout(1000) });
      return res.ok;
    } catch {
      return false;
    }
  }

  async getFarmers(): Promise<Farmer[]> {
    if (this.useMock) {
      return MOCK_FARMERS;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/farmers`);
      if (!res.ok) throw new Error('API failed');
      const data = await res.json();
      // Map Neo4j format to Frontend Farmer format if needed
      return data.map((item: any) => ({
        id: item.id || item.phone,
        full_name: item.full_name || 'Unnamed Farmer',
        phone: item.phone || '',
        gender: item.gender || '',
        age: item.age || 0,
        location: item.location || '',
        farming_type: item.farming_type || '',
        status: item.status || 'active',
        registration_date: item.registration_date
      }));
    } catch (e) {
      console.warn('API error, falling back to mock farmers', e);
      return MOCK_FARMERS;
    }
  }

  async getFarmer(id: string): Promise<Farmer | null> {
    if (this.useMock) {
      return MOCK_FARMERS.find(f => f.id === id) || null;
    }
    try {
      const res = await fetch(`${BACKEND_URL}/farmers/${id}`);
      if (!res.ok) throw new Error('API failed');
      const data = await res.json();
      const item = Array.isArray(data) ? data[0] : data;
      if (!item) return null;
      return {
        id: item.id || item.phone,
        full_name: item.full_name || 'Unnamed Farmer',
        phone: item.phone || '',
        gender: item.gender || '',
        age: item.age || 0,
        location: item.location || '',
        farming_type: item.farming_type || '',
        status: item.status || 'active',
        registration_date: item.registration_date
      };
    } catch (e) {
      console.warn(`API error for farmer ${id}, falling back to mock`, e);
      return MOCK_FARMERS.find(f => f.id === id) || null;
    }
  }

  async getVerificationResult(farmerId: string): Promise<FinalResult | null> {
    if (this.useMock) {
      return MOCK_VERIFICATION_RESULTS[farmerId] || null;
    }
    try {
      const farmer = await this.getFarmer(farmerId);
      if (!farmer) return null;
      
      const mockResult = Object.values(MOCK_VERIFICATION_RESULTS).find(
        r => r.farmer_name.toLowerCase() === farmer.full_name.toLowerCase()
      );
      if (!mockResult) return null;

      const res = await fetch(`${BACKEND_URL}/api/verify/${mockResult.session_id}/result`);
      if (!res.ok) throw new Error('API failed');
      return await res.json();
    } catch (e) {
      console.warn(`API error for result of farmer ${farmerId}, falling back to mock`, e);
      const farmer = await this.getFarmer(farmerId);
      if (farmer) {
        const mockResult = Object.values(MOCK_VERIFICATION_RESULTS).find(
          r => r.farmer_name.toLowerCase() === farmer.full_name.toLowerCase()
        );
        if (mockResult) return mockResult;
      }
      return MOCK_VERIFICATION_RESULTS[farmerId] || null;
    }
  }

  async getLogs(session_id: string, farmerId: string): Promise<VerificationLog[]> {
    if (this.useMock) {
      return MOCK_VERIFICATION_LOGS[farmerId] || [];
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/verify/${session_id}/logs`);
      if (!res.ok) throw new Error('API failed');
      const data = await res.json();
      return data.events || [];
    } catch (e) {
      const farmer = await this.getFarmer(farmerId);
      if (farmer) {
        const key = Object.keys(MOCK_VERIFICATION_RESULTS).find(
          k => MOCK_VERIFICATION_RESULTS[k].farmer_name.toLowerCase() === farmer.full_name.toLowerCase()
        );
        if (key && MOCK_VERIFICATION_LOGS[key]) return MOCK_VERIFICATION_LOGS[key];
      }
      return MOCK_VERIFICATION_LOGS[farmerId] || [];
    }
  }

  async startVerification(farmerId: string): Promise<any> {
    if (this.useMock) {
      // Simulate starting verification
      const farmer = MOCK_FARMERS.find(f => f.id === farmerId);
      if (farmer) {
        MOCK_VERIFICATION_RESULTS[farmerId] = {
          session_id: `sess-${farmerId}`,
          farmer_id: farmerId,
          farmer_name: farmer.full_name,
          status: 'pending',
          created_at: new Date().toISOString(),
          trust_score: 50.0,
          decision: 'REVIEW_REQUIRED',
          recommendation: 'REVIEW',
          participant_scores: [
            {
              participant_type: 'Chief',
              participant_name: 'Chief Njoroge',
              phone: '0711223344',
              status: 'pending',
              raw_score: 0,
              weight: 4,
              weighted_score: 0,
              responses: []
            },
            {
              participant_type: 'Agrovet Owner',
              participant_name: 'Green Agrovet',
              phone: '0755443322',
              status: 'pending',
              raw_score: 0,
              weight: 3,
              weighted_score: 0,
              responses: []
            }
          ],
          analysis: {
            summary: 'Verification process started.',
            explanation: 'Active verification session started in mock mode. Awaiting SMS responses from verifiers.',
            key_drivers: [],
            risk_factors: ['Awaiting responses from Chief and Agrovet.']
          }
        };
      }
      return { success: true, message: 'Verification started in mock mode.' };
    }
    try {
      const res = await fetch(`${BACKEND_URL}/api/verify/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ farmer_id: farmerId })
      });
      if (!res.ok) throw new Error('API failed');
      return await res.json();
    } catch (e) {
      throw e;
    }
  }

  async getTestifiers(): Promise<Testifier[]> {
    // Backend doesn't have a direct testifier list endpoint, so mock is the main source of truth
    return MOCK_TESTIFIERS;
  }

  async approveLoan(_sessionId: string): Promise<boolean> {
    // In a live system, this registers loan approval in the database or sends a webhook callback
    if (this.useMock) return true;
    try {
      // Mock sending loan approval
      await new Promise(resolve => setTimeout(resolve, 500));
      return true;
    } catch {
      return false;
    }
  }

  async declineLoan(_sessionId: string): Promise<boolean> {
    if (this.useMock) return true;
    return true;
  }

  async requestMoreInfo(_sessionId: string): Promise<boolean> {
    if (this.useMock) return true;
    return true;
  }
}

export const api = new ApiService();
