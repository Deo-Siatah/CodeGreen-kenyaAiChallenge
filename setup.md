# AgriForesight MVP Implementation Plan

## Alternative Agricultural Credit Scoring Through Social Infrastructure, Graph Verification, and AI Explainability

---

# 1. Executive Summary

## The Problem

Millions of smallholder farmers across Kenya remain excluded from formal credit because traditional lending systems rely heavily on collateral such as land titles, property ownership, and formal financial histories.

This disproportionately affects:

- Youth
- Women
- Persons with Disabilities (PWDs)
- First-time farmers
- Informal rural producers

Many of these farmers are productive and capable of repaying loans but cannot provide traditional forms of security. As a result, financial institutions classify them as high-risk despite the existence of strong community-based trust signals and repayment evidence.

---

## Why Collateral-Based Lending Fails

Traditional lending asks:

> What assets do you own?

AgriForesight asks:

> What evidence exists that you can repay?

Collateral measures asset ownership.

It does not measure:

- Character
- Community trust
- Production capacity
- Financial discipline
- Savings behavior
- Market access
- Repayment intent

Many farmers possess these qualities but remain invisible to formal lenders.

---

## Our Solution

AgriForesight is an AI-powered alternative agricultural credit scoring platform that combines:

### Quantitative Signals

- M-Pesa activity
- Utility payment history
- Cooperative delivery records
- Previous loan performance
- Seasonal income patterns

### Qualitative Signals

- Chief testimony
- Agrovet testimony
- School testimony
- Chama participation
- Community endorsements
- In-kind settlement proof
- Farm production plans

These signals are verified, weighted, and transformed into an explainable credit score that works on:

- USSD
- SMS
- Voice calls
- SACCO dashboards

The platform remains accessible to feature phone users while producing transparent credit decisions in English and Kiswahili.

---

## Core Differentiators

### Social Infrastructure as Credit Infrastructure

Instead of relying on assets, AgriForesight formalizes:

- Community trust
- Social accountability
- Production evidence
- Savings discipline

into measurable risk signals.

### Graph-Based Verification

Neo4j models relationships between:

- Farmers
- Chiefs
- Chamas
- Cooperatives
- Agrovets
- Schools

This enables fraud detection and trust analysis.

### Explainable AI

Every score can be translated into:

- Loan officer reasoning
- Farmer-friendly explanations
- Kiswahili SMS
- Voice-call narratives

### Youth Cold Start Pathway

Young farmers without assets or financial history can still qualify through:

- Registration
- Testimony
- Farm plans
- Savings discipline

rather than being automatically rejected.

---

# 2. MVP Definition

## Included in MVP

### Farmer Onboarding

Capture:

- Farmer profile
- Location
- Farm details
- Crop information

### Social Graph Creation

Create and manage:

- Farmer ↔ Chief
- Farmer ↔ Agrovet
- Farmer ↔ Chama
- Farmer ↔ School
- Farmer ↔ Cooperative

relationships.

### Multi-Authority Verification

Verification through:

- SMS
- Dashboard
- Manual confirmation

### Rule-Based Credit Scoring

Transparent scoring engine.

No machine learning required.

### AI Explainability

Generate:

- Loan officer explanations
- Farmer explanations
- Kiswahili translations

### SMS Notifications

- Verification requests
- Approval notices
- Rejection notices

### USSD Interface

For field loan officers and feature-phone workflows.

### SACCO Dashboard

For assessment, approvals, monitoring, and portfolio analytics.

---

## Excluded From MVP

- Full banking integrations
- Live M-Pesa integrations
- Advanced ML scoring models
- Satellite monitoring
- Climate prediction engines
- Mobile applications
- Regulatory integrations

These remain future roadmap items.

---

# 3. System Architecture

```text
Farmer
   │
   ├── USSD
   ├── SMS
   └── Voice Call
            │
            ▼
    Africa's Talking
            │
            ▼
      FastAPI Backend
            │
 ┌──────────┼──────────┐
 │          │          │
 ▼          ▼          ▼
Neo4j    AI Layer   SMS Layer
 │          │          │
 ▼          ▼          ▼
Graph   Explainability Notifications
Storage Translation
            │
            ▼
     Scoring Engine
            │
            ▼
     Recommendation
            │
            ▼
      SACCO Dashboard
```

---

## Component Responsibilities

### Neo4j

Acts as the sole database for the MVP.

Stores:

- Farmers
- Authorities
- Chamas
- Cooperatives
- Farms
- Loans
- Verification sessions
- Authority responses
- Score profiles
- Recommendations
- Notifications
- Audit logs
- User accounts
- Graph relationships

Used for:

- Verification
- Fraud detection
- Social trust analysis
- Credit scoring
- Loan tracking
- Dashboard reporting

### Scoring Engine

Combines:

- Quantitative signals
- Qualitative signals
- Risk deductions

into a final score.

### AI Layer

Transforms scores into:

- Human-readable reasoning
- Kiswahili translations
- Voice-ready scripts

### Dashboard

Allows SACCOs to:

- Review profiles
- Monitor verifications
- Approve loans
- Analyze portfolio performance

---
# 4. Database Design (Neo4j Only)

## Database Philosophy

AgriForesight is built around the idea that creditworthiness can be demonstrated through multiple forms of social, economic, and behavioral evidence.

Rather than assuming every farmer has access to formal institutions, the platform allows trust and repayment evidence to originate from a wide variety of community actors.

The graph therefore models:

- People
- Institutions
- Social Groups
- Market Relationships
- Economic Activities
- Verification Evidence
- In-Kind Transactions
- Loan Histories

This allows the platform to adapt to different regions, communities, and farming systems without redesigning the database.

---

## Core Node Categories

### Farmer

Represents a farmer seeking credit.

Properties:

- id
- full_name
- phone
- gender
- age
- location
- farming_type
- registration_date

---

### Trust Source

Represents any individual capable of providing testimony or verification.

Examples:

- Chief
- Assistant Chief
- Village Elder
- Religious Leader
- Teacher
- School Head
- Health Worker
- Agrovet Owner
- Cooperative Officer
- SACCO Officer
- Neighbor
- Landlord
- Produce Buyer
- Employer
- Community Leader

Properties:

- id
- name
- category
- phone
- location
- credibility_score

The category field allows expansion without database redesign.

---

### Institution

Represents formal or semi-formal organizations.

Examples:

- School
- Cooperative
- SACCO
- Church
- Mosque
- NGO
- Farmer Organization
- Health Facility
- Community Based Organization (CBO)

Properties:

- id
- name
- institution_type
- location

---

### Social Group

Represents informal community groups.

Examples:

- Chama
- Savings Group
- Youth Group
- Women's Group
- Self Help Group
- Producer Group

Properties:

- id
- name
- group_type
- location

---

### Market Actor

Represents economic relationships.

Examples:

- Produce Buyer
- Trader
- Broker
- Aggregator
- Retailer
- Wholesaler
- Shop Owner
- Input Supplier

Properties:

- id
- name
- actor_type
- location

---

### Farm

Properties:

- id
- acreage
- production_type
- primary_crop
- location

---

### Loan

Properties:

- id
- amount
- status
- application_date
- approval_date

---

### Verification Session

Represents an active verification process.

Properties:

- id
- status
- created_at
- expires_at

---

### Testimonial

Represents an endorsement submitted by a trust source.

Properties:

- id
- rating
- comments
- confidence_level
- timestamp

---

### Buyer Testimonial

Represents market-based repayment evidence.

Examples:

- Consistent banana supplier
- Reliable milk seller
- Trusted maize producer
- Frequent produce vendor

Properties:

- id
- purchase_frequency
- years_of_relationship
- estimated_volume
- reliability_rating

---

### In-Kind Settlement Proof

Represents non-cash repayment behavior.

Examples:

- Livestock exchanged for debt
- Produce supplied against credit
- Inputs repaid through harvest
- Labor exchanged for obligations

Properties:

- id
- settlement_type
- estimated_value
- verification_status
- date_recorded

---

### Financial Signal

Represents structured financial evidence.

Examples:

- Mobile money activity
- Utility payment record
- SACCO savings activity
- Cooperative delivery records

Properties:

- id
- signal_type
- score
- period

---

### Score Profile

Properties:

- id
- total_score
- trust_score
- financial_score
- risk_score
- generated_at

---

### Recommendation

Properties:

- id
- decision
- explanation
- generated_at

---

### Notification

Properties:

- id
- type
- recipient
- message
- sent_at

---

## Relationship Model

### Identity & Farm Relationships

```text
(Farmer)-[:OWNS]->(Farm)

(Farmer)-[:APPLIED_FOR]->(Loan)

(Farmer)-[:HAS_SCORE]->(ScoreProfile)

(Farmer)-[:RECEIVED]->(Recommendation)
```

### Social Trust Relationships

```text
(Farmer)-[:VERIFIED_BY]->(TrustSource)

(TrustSource)-[:SUBMITTED]->(Testimonial)

(Testimonial)-[:SUPPORTS]->(Farmer)
```

### Institutional Relationships

```text
(Farmer)-[:MEMBER_OF]->(Institution)

(Farmer)-[:ASSOCIATED_WITH]->(Institution)

(TrustSource)-[:WORKS_FOR]->(Institution)
```

### Social Group Relationships

```text
(Farmer)-[:MEMBER_OF]->(SocialGroup)

(SocialGroup)-[:ENDORSES]->(Farmer)
```

### Market Relationships

```text
(Farmer)-[:SELLS_TO]->(MarketActor)

(MarketActor)-[:PROVIDED]->(BuyerTestimonial)

(BuyerTestimonial)-[:SUPPORTS]->(Farmer)
```

### In-Kind Settlement Relationships

```text
(Farmer)-[:PROVIDED]->(InKindSettlementProof)

(InKindSettlementProof)-[:VALIDATED_BY]->(TrustSource)
```

### Verification Relationships

```text
(Farmer)-[:PARTICIPATED_IN]->(VerificationSession)

(VerificationSession)-[:COLLECTED]->(Testimonial)

(VerificationSession)-[:COLLECTED]->(BuyerTestimonial)

(VerificationSession)-[:COLLECTED]->(InKindSettlementProof)
```

### Financial Evidence Relationships

```text
(Farmer)-[:HAS_SIGNAL]->(FinancialSignal)

(FinancialSignal)-[:CONTRIBUTES_TO]->(ScoreProfile)
```

---

## Why This Model Works

This model accommodates multiple realities:

### Farmer A

May be verified by:

- Chief
- SACCO Officer
- Agrovet

### Farmer B

May be verified by:

- Village Elder
- Church Leader
- Chama Chairperson

### Farmer C

May have no authority figure available but can provide:

- Produce buyer testimonials
- Savings group endorsements
- In-kind repayment evidence

### Farmer D

May be a youth farmer with:

- Farm plan
- Group membership
- Community testimony

The database remains unchanged because all evidence sources are treated as graph entities rather than hardcoded roles.

---

## Fraud Detection Opportunities

Neo4j enables:

### Suspicious Verifier Detection

```text
Village Elder A
 ├── Farmer 1 (Default)
 ├── Farmer 2 (Default)
 ├── Farmer 3 (Default)
```

### Fake Buyer Networks

```text
Buyer X
 ├── Farmer A
 ├── Farmer B
 ├── Farmer C
```

Unusual endorsement patterns can be flagged.

### Trust Reputation Scoring

Every verifier, institution, group, or buyer can accumulate a credibility score based on the historical performance of farmers they supported.

This creates a self-improving trust infrastructure for agricultural finance.


# 5. Backend Architecture

## Technology Stack

### Backend

- Python
- FastAPI
- Neo4j Driver
- Pydantic

### Infrastructure

- Docker
- Railway / Render

---

## Architecture Layers

### Repository Layer

Responsibilities:

- Neo4j queries
- CRUD operations
- Graph traversal

### Service Layer

Responsibilities:

- Verification logic
- Authority weighting
- Scoring calculations
- Fraud detection
- AI orchestration

### Controller Layer

Responsibilities:

- Input validation
- Request handling
- Response formatting

---

## External Integrations

### SMS

Africa's Talking

### USSD

Africa's Talking

### AI

Google Gemini API

### Voice

Google Text-to-Speech

---

# 6. Credit Scoring Engine

## Scoring Philosophy

```text
Ability to Repay
+
Likelihood to Repay
+
Community Trust
-
Risk Factors
```

## Quantitative Signals

| Signal | Weight |
|----------|----------|
| M-Pesa Activity | 30 |
| Utility Payments | 20 |
| Loan History | 30 |
| Cooperative Deliveries | 20 |

## Qualitative Signals

| Signal | Weight |
|----------|----------|
| Chief Testimony | 25 |
| Agrovet Testimony | 15 |
| School Testimony | 10 |
| Chama Participation | 15 |
| Farm Plan | 15 |
| In-kind Proofs | 15 |

## Youth Cold Start Pathway

- Registration: +10
- Community Testimony: +20–50
- Farm Plan: +8–15
- Savings Discipline: +5–15
- Additional Testifiers: +10–15 each

## Climate Adjustments

- Drought Risk = -5
- Pest Risk = -5

## Decision Bands

| Score | Decision |
|---------|---------|
| 80–100 | Approve |
| 65–79 | Conditional Approve |
| 50–64 | Development Pathway |
| Below 50 | Decline |

---

# 7. Multi-Layer Verification Engine

## Supported Verifiers

- Chief
- School Head
- Agrovet
- Chama Chair
- Neighbor
- Cooperative Officer
- Health Worker

## Authority Weighting

| Authority | Weight |
|------------|----------|
| Chief | 5x |
| Agrovet | 3x |
| School Head | 2.5x |
| Health Worker | 2.5x |
| Neighbor | 1x |

## Verification Workflow

1. Farmer submits authority contacts.
2. System sends SMS.
3. Responses stored in Neo4j.
4. Verification score updated.
5. Credit score recalculated.

### Non-Response Handling

- Provisional Score
- Partial Score
- Final Score
- Timeout after 48 hours

---

# 8. AI Layer

## Primary AI Use Cases

### Explainability

Convert:

```text
Signals
+
Score
+
Risks
```

into human reasoning.

### Translation

- English
- Kiswahili

### Voice Generation

Generate voice-ready explanations.

## Recommended AI Stack

- Google Gemini
- Google AI SDK
- Google Text-to-Speech

## Fallback Strategy

```text
Template Engine
+
Stored Message Templates
```

---

# 9. Input Channels

## USSD

- Farmer lookup
- Verification status
- Score retrieval
- Approval workflow

## SMS

- Authority verification
- Loan updates
- Approval notices

## Voice

- Read explanations aloud
- Accessibility support
- Local language communication

---

# 10. SACCO Dashboard

## Frontend Stack

- React
- TypeScript
- TailwindCSS

## Features

### Portfolio Dashboard

- Farmers assessed
- Approval rates
- Loan volumes
- Repayment rates

### Farmer Profile

- Signals
- Authorities
- Verifications
- Scores
- AI reasoning

### Graph View

Visualizes trust relationships and endorsements.

### Fraud Analytics

Flags:

- Suspicious authorities
- Excessive endorsements
- Default clusters

---

# 11. Deployment Plan

## Backend

- Render
- Railway

## Frontend

- Vercel

## Database

- Neo4j Aura Free

## Communications

- Africa's Talking

## AI

- Google Gemini

---

# 12. Development Phases

## Phase 1 — Foundation

- Neo4j schema design
- Authentication
- Farmer onboarding
- Graph modeling

## Phase 2 — Verification

- SMS workflows
- Authority responses
- Verification engine

## Phase 3 — Scoring

- Rule engine
- Risk calculations
- Recommendations

## Phase 4 — AI

- Explainability
- Translation
- Voice generation

## Phase 5 — Dashboard

- Portfolio analytics
- Graph visualization
- Fraud monitoring

## Phase 6 — Deployment

- Hosting
- Testing
- Demo preparation

---

# 13. Core API Design

```http
POST /farmers
POST /authorities
POST /verification/start
POST /verification/respond
GET /verification/{id}
GET /score/{farmer_id}
POST /score/recalculate
POST /ai/explain
POST /voice/generate
GET /dashboard
GET /graph/{farmer_id}
POST /loan/approve
POST /loan/reject
```

---

# 14. Folder Structure

```text
agroforesight/

backend/
├── app/
│   ├── api/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   ├── ai/
│   ├── scoring/
│   ├── verification/
│   ├── graph/
│   └── core/

frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── hooks/
│   ├── services/
│   ├── graph/
│   └── dashboard/

infrastructure/
├── docker/
├── deployment/
└── scripts/
```

---

# 15. Hackathon Demo Flow

1. Add Farmer
2. Add Authorities
3. Trigger Verification
4. Receive Responses
5. Generate Score
6. Generate AI Explanation
7. Show Neo4j Graph
8. Approve Loan
9. Send SMS
10. Generate Voice Output

Demonstrates:

- Alternative scoring
- Explainability
- Accessibility
- Graph verification
- Fraud detection
- Real-world viability

---

# 16. Potential Challenges and Mitigation

| Challenge | Impact | Mitigation |
|------------|----------|------------|
| Delayed verification | Provisional scoring |
| Fake testimony | Fraud risk | Multi-authority corroboration |
| SMS delivery failures | Missing evidence | Dashboard/manual verification |
| Sparse farmer data | Low confidence | Youth cold-start pathway |
| Authority collusion | False approvals | Reputation scoring and audits |
| Climate shocks | Repayment risk | Climate risk deductions |
| AI API downtime | Missing explanations | Template fallback engine |
| USSD session timeouts | Poor UX | Persistent verification sessions |
| Network issues | Rural accessibility | SMS-first architecture |
| Graph growth | Query performance | Neo4j indexing and optimization |

---

# Vision Statement

**AgriForesight transforms social trust into financial trust.**

By combining community verification, behavioral signals, graph intelligence, and explainable AI, the platform enables SACCOs to lend confidently to farmers who have traditionally been excluded from formal credit systems, making the invisible farmer visible to finance.