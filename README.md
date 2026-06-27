# Hifadhi: Giving invisible farmers a credit history

**Alternative Agricultural Credit Scoring Through Social Infrastructure, Graph Verification, and AI Explainability.**

---

## 1. Overview
Millions of smallholder farmers across Kenya remain excluded from formal credit because traditional lending systems rely heavily on collateral (such as land titles or property ownership) and formal credit histories. This disproportionately affects youth, women, PWDs, and first-time farmers who are productive and capable of repaying loans but remain invisible to formal financial institutions.

**Hifadhi** (meaning *to preserve/save* in Swahili) solves this by mapping community trust signals—including local elder testimony, school fee records, Chama savings activity, and cooperative delivery histories—into a relationship graph database. By leveraging social infrastructure as credit infrastructure, Hifadhi extracts verified community trust networks to construct a reliable alternative credit profile.

Developed for **AFRACA's official "Invisible Farmer" brief** under the **Mercy Corps AgriFin track** of the **Kenya AI Challenge**, Hifadhi is built by **Team Code Green** to bridge the gap between rural community trust and formal financial eligibility.

---

## 2. Key Features
* **Graph-Based Risk Profiling (Neo4j):** Models multi-node relationships between farmers, farms, local chiefs, savings groups, cooperatives, and buyers to identify and prevent collusive vouching loops.
* **Dynamic Trust Weighting Engine:** Computes alternative credit scores based on verifier node credibility (e.g., Chiefs/SACCO officers are weighted at `4.0`, neighbors at `1.0`).
* **Social Accountability Penalties:** Implements a timeout scoring system where non-responsive verifiers are penalized to `0` but their weights remain in the score calculation, discouraging unverified profiles.
* **AI Explainability (Gemini 2.5 Flash):** Translates complex graph clusters and scores into natural, explainable text in English and Swahili, outlining key score drivers and risk factors.
* **Integrated USSD/SMS Verification (Africa's Talking):** Fully integrated callback handlers for SMS vouching requests and interactive USSD response callbacks.
* **Premium Admin Dashboard:** Real-time monitoring portal for credit officers to start verification sessions, audit verification logs, and view explainability scores.
* **Dynamic Connection Settings:** An interactive Settings menu (`⚙️`) in the UI that stores custom backend URLs in the browser's local storage—ideal for hot-swapping temporary ngrok/localtunnel URLs during testing.

---

## 3. Tech Stack
* **Backend:**
  * Framework: FastAPI (Python 3.12+)
  * Server: Uvicorn
  * Database: Neo4j Graph Database
  * AI SDK: `google-generativeai` (Gemini 2.5 Flash)
  * Telecom Integration: `africastalking` SDK
  * Schemas & Settings: `pydantic` & `pydantic-settings`
* **Frontend:**
  * Framework: React 19
  * Build Tool: Vite 8.1.0
  * Language: TypeScript 6.0
  * CSS Framework: Tailwind CSS v4
  * Icons: `lucide-react`
* **Hosting & Deployment:**
  * Frontend: Netlify
  * Backend: Render

---

## 4. Architecture Overview

```
               +-------------------------------------------+
               |         Admin Dashboard (React)           |
               +---------------------+---------------------+
                                     | (API Requests)
                                     v
                       +-------------+-------------+
                       |       FastAPI Backend     |
                       +-------------+-------------+
                                     |
             +-----------------------+-----------------------+
             |                       |                       |
             v                       v                       v
     +-------+-------+       +-------+-------+       +-------+-------+
     |  Neo4j Aura   |       | Google Gemini |       | Africa's      |
     |  Graph DB     |       | (Explainability|      | Talking       |
     +---------------+       +---------------+       +-------+-------+
                                                             |
                                                             v (SMS/USSD)
                                                     +-------+-------+
                                                     | Verifiers /   |
                                                     | Farmers       |
                                                     +---------------+
```

1. **Verification Initiated:** A loan officer requests verification on the Dashboard.
2. **Session Creation:** FastAPI creates a `VerificationSession` node in Neo4j and queries the graph for the farmer's registered `TrustSources`.
3. **Telecom Outreach:** The backend sends SMS vouching prompts to verifiers via Africa's Talking.
4. **Trust Validation:** Verifiers respond to prompts either by replying to the SMS or by dialing the USSD shortcode.
5. **Score Aggregation:** When all participants respond (or the session times out), the backend runs Cypher queries to compute the final weighted trust score.
6. **AI Explanation:** Gemini 2.5 Flash generates a structured natural language analysis based on the scoring results.
7. **Notification:** The final decision is sent as a text notification back to the farmer, and the dashboard is updated.

---

## 5. Graph Data Model

The application enforces strict data constraints and index configurations inside Neo4j. The node types and relationships implemented include:

### Node Labels
* `Farmer`: Primary profile storing identity data (phone, location, registration date).
* `Farm`: Details of the farmer's property and production details.
* `TrustSource`: Registered verifiers (e.g., Chiefs, Elders, Teachers, Agrovets).
* `Institution` / `SocialGroup`: SACCOs, Cooperatives, and local Chamas.
* `MarketActor`: Aggregators and buyers purchasing the farmer's produce.
* `Testimonial`: Digital record of a verifier's character vouching.
* `BuyerTestimonial`: Delivery and transaction histories provided by buyers.
* `InKindSettlementProof`: Records of non-cash payments (e.g., school fee settlements).
* `VerificationSession`: Active auditing records representing current verification sessions.
* `FinancialSignal`: Individual transaction metrics.
* `ScoreProfile` / `Recommendation`: Calculated risk classifications and loan decisions.

### Relationships
* `(Farmer)-[:OWNS]->(Farm)`
* `(Farmer)-[:VERIFIED_BY]->(TrustSource)`
* `(Farmer)-[:MEMBER_OF]->(Institution | SocialGroup)`
* `(Farmer)-[:SELLS_TO]->(MarketActor)`
* `(TrustSource)-[:SUBMITTED]->(Testimonial)-[:SUPPORTS]->(Farmer)`
* `(MarketActor)-[:PROVIDED]->(BuyerTestimonial)-[:SUPPORTS]->(Farmer)`
* `(Farmer)-[:PROVIDED]->(InKindSettlementProof)-[:VALIDATED_BY]->(TrustSource)`
* `(Farmer)-[:PARTICIPATED_IN]->(VerificationSession)-[:COLLECTED]->(Testimonial)`
* `(Farmer)-[:HAS_SIGNAL]->(FinancialSignal)-[:CONTRIBUTES_TO]->(FinancialScore)`
* `(Farmer)-[:HAS_SCORE]->(ScoreProfile)`
* `(Farmer)-[:RECEIVED]->(Recommendation)`

---

## 6. Getting Started & Installation

### Prerequisites
* **Python** (version 3.12 or higher)
* **Node.js** (version 18 or higher)
* **Neo4j Instance:** A free cloud instance on Neo4j Aura DB or a local Neo4j Community Server.

---

### Step 1: Clone the Repository
```bash
git clone https://github.com/Deo-Siatah/CodeGreen-kenyaAiChallenge.git
cd CodeGreen-kenyaAiChallenge
```

---

### Step 2: Backend Installation & Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```
3. Install dependencies in editable mode:
   ```bash
   pip install -e .
   ```
4. Create a `.env` file in the `backend` folder and populate it with your credentials (see the **Environment Variables** table below).
5. Initialize constraints and indexes in your Neo4j database:
   ```bash
   python scripts/init_graph.py
   ```
6. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload
   ```

---

### Step 3: Frontend Installation & Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser and navigate to `http://localhost:5173`.

---

## 7. Environment Variables

Create a `.env` file in the `/backend` folder with the following variables:

| Environment Variable | Required | Description |
| :--- | :---: | :--- |
| `APP_NAME` | Yes | Name of the application (e.g. `AgriForesight`) |
| `NEO4J_URI` | Yes | Bolt connection string for your database (e.g. `neo4j+s://...`) |
| `NEO4J_USERNAME` | Yes | Username for your Neo4j instance |
| `NEO4J_PASSWORD` | Yes | Password for your Neo4j instance |
| `NEO4J_DATABASE` | Yes | Name of the default database |
| `BACKEND_URL` | Yes | Host address of your running backend (e.g. `http://localhost:8000` or ngrok URL) |
| `USSD_WEBHOOK_URL` | Yes | The callback URL registered in Africa's Talking for USSD callbacks |
| `SMS_WEBHOOK_URL` | Yes | The callback URL registered in Africa's Talking for incoming SMS webhooks |
| `AFRICASTALKING_USERNAME` | Yes | Your Africa's Talking account username (use `sandbox` for testing) |
| `AFRICASTALKING_API_KEY` | Yes | The API key generated from your Africa's Talking developer dashboard |
| `GEMINI_API_KEY` | Yes | Google Gemini API key to activate natural language explainability features |

---

## 8. Project Structure

```text
CodeGreen-kenyaAiChallenge/
├── backend/
│   ├── api/                   # FastAPI route controllers (farmers, relationships, ussd, verification)
│   ├── core/                  # Configuration loaders, settings, and database connector
│   ├── graph/                 # Database schemas, unique constraints, and indexes
│   ├── prompts/               # System and context formatting prompts for Gemini
│   ├── repositories/          # Neo4j Cypher query interfaces
│   ├── schemas/               # Pydantic request and response models
│   ├── scripts/               # Graph database seeding and automated test scripts
│   ├── services/              # Core scoring, AI explanation, USSD, and SMS business logic
│   ├── utils/                 # Utility files (phone normalization, logging, helper functions)
│   ├── main.py                # FastAPI app entrypoint
│   ├── Dockerfile
│   └── pyproject.toml         # Backend package definitions and dependencies
├── frontend/
│   ├── src/
│   │   ├── assets/            # Static image assets
│   │   ├── components/        # Dashboard, FarmerList, FarmerDetail, TestifiersView components
│   │   ├── services/          # Unified API service layer with local storage configuration
│   │   ├── App.css
│   │   ├── App.tsx            # App structure and tab layouts
│   │   ├── index.css          # Tailwind imports
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json           # Frontend dependency declarations
│   └── vite.config.ts
├── setup.md                   # MVP implementation logs and developer notes
└── README.md                  # This file
```

---

## 9. Current Status & Known Limitations
* **Fully Working:**
  * Schema creation, Cypher graph query generation, and Neo4j database insertions.
  * Quantitative scoring algorithms (dynamic weighting based on participant type).
  * Auto-generation of USSD callback formats and verification profiles.
  * Live **Gemini AI Explainability Engine** generating natural language summaries.
  * **Africa's Talking SMS Service** sending live text notifications.
* **Simulated/Sandboxed:**
  * **Verifier Response Simulator:** The admin dashboard features an interactive console that simulates USSD and SMS verifier responses locally. This allows you to evaluate scoring updates without incurring SMS delivery fees.
* **Limitations:**
  * USSD requires standard shortcode provisioning from telecom companies to go live outside Africa's Talking developer sandbox.
  * The credit score is static once calculated and requires manual trigger re-evaluations if new relationships are appended.

---

## 10. Team
**Team Code Green:**
* **Deo Siatah** (Lead Software Engineer / Graph Architecture)
* **Laura Shaviya** (Frontend Developer / UX Lead)
* **Dancan Mibei** (Database Administrator / Scoring Logic)
* **Rebeca Agai** (AI Prompt Engineer / QA Specialist)
* **Said Kombe** (Systems Integrator / Telecom Operations)

---

## 11. Acknowledgments
* **AFRACA (African Rural and Agricultural Credit Association)** for the "Invisible Farmer" challenge brief.
* **Mercy Corps AgriFin** for the AgriFin track and mentoring.
* **Neo4j** for providing powerful graph database solutions to map community trust networks.
