# Hifadhi: giving invisible farmers a credit history

**Alternative agricultural credit scoring through community verification, a relational trust graph, and explainable AI.**

Hifadhi (Swahili for *to preserve/save*) is built by **Team Code Green** for the **Kenya AI Challenge**, responding to AFRACA's **"Invisible Farmer"** brief under the **Mercy Corps AgriFin** track.

---

## 1. Overview

Millions of smallholder farmers in Kenya remain excluded from formal credit because lending still depends on collateral and formal credit history. Hifadhi builds an alternative credit profile from evidence that already exists in rural communities:

- community testimony from chiefs, elders, teachers, and neighbours
- buyer and agrovet relationships
- Chama/SACCO contribution discipline
- in-kind settlement records
- satellite-derived farm activity, where available

The result is a deterministic, auditable score with a full component breakdown, a loan recommendation, and a plain-language explanation in English or Kiswahili.

---

## 2. What is implemented

- **Six-step case workflow** in the frontend: farmer, farm, network, verification, score, loan.
- **Live trust graph** rendered from the API response, with force layout, reduced-motion support, and a recorded replay.
- **Portfolio and analytics dashboards** backed by real endpoints: score distribution, decision mix, county coverage, loan book, response rate, component averages, and fairness indicators.
- **Two-axis scoring**: a character axis from community, buyer, discipline, and settlement signals; an optional capacity axis from farm activity.
- **Verifier credibility** and pooled testimony with a category-diversity bonus.
- **Explainability API** that sends only a privacy-reduced score breakdown to the configured provider and returns expert- or farmer-facing prose.
- **Loan lifecycle**: create against an eligible score, disburse, repay, or default.
- **English/Kiswahili UI** and a persisted light/dark theme.

The UI is driven by an event log and a pure reducer in `frontend/src/domain/graph`; components do not mutate graph state directly.

---

## 3. Tech stack

### Backend

| Concern | Choice |
| --- | --- |
| Framework | FastAPI, Python 3.12+ |
| Database | PostgreSQL on Neon |
| ORM / driver | SQLAlchemy 2 async + asyncpg |
| Migrations | Alembic |
| Validation / settings | Pydantic v2 + pydantic-settings |
| Package manager | uv |
| Explainability | Groq via `langchain-groq` (provider is swappable) |
| Farm activity | Google Earth Engine, optional; null provider by default |

Neo4j is no longer the primary store. The old `NEO4J_*` settings remain temporarily required by `Settings` but are marked deprecated.

### Frontend

| Concern | Choice |
| --- | --- |
| Framework | React 19 + TypeScript 6 |
| Build | Vite 8 |
| Styling | Tailwind CSS 4 + design tokens in `src/styles/tokens.css` |
| Components | shadcn/ui + Radix primitives |
| Data | TanStack Query + axios |
| Contracts | Zod at every API boundary + generated OpenAPI types |
| State | Zustand for graph/case state; pure reducer in `src/domain` |
| Motion / graph | Motion + d3-force |
| i18n | In-house English/Kiswahili dictionary |
| Tests | Vitest + Testing Library; Playwright for e2e |

Design language: **"night harvest"** — near-black green canvas, luminous graph nodes, restrained motion. Fonts are Fraunces, Hanken Grotesk, and JetBrains Mono, self-hosted.

---

## 4. Architecture

```text
                    +----------------------------------+
                    |  React SPA (Vite)                |
                    |  portfolio / analytics / case    |
                    +----------------+-----------------+
                                     | HTTPS + Zod validation
                                     v
                    +----------------------------------+
                    |  FastAPI                         |
                    |  api -> services -> repositories |
                    +----+-------------+---------------+
                         |             |
             SQLAlchemy  |             |  provider call
                         v             v
              +------------------+   +----------------------+
              | Postgres (Neon)  |   | Groq explanation API |
              | relational trust |   +----------------------+
              | graph + scoring  |
              +--------+---------+
                       |
                       | optional
                       v
              +------------------+
              | Google Earth     |
              | Engine (NDVI)    |
              +------------------+
```

Request flow:

1. A loan officer creates a farmer, farm, and network links.
2. `POST /api/verify/start` snapshots linked trust sources, market actors, and social groups into a verification session.
3. Responses are submitted per participant. Each response writes a typed signal row.
4. When every participant has responded or timed out, the scoring service computes and persists a new `ScoreProfile` version plus its `ScoreComponent` rows.
5. The breakdown endpoint exposes the full calculation; the explanation endpoint adds provider-generated prose.
6. Eligible scores can be used to create and resolve loans.
7. The frontend renders every step from the API response through the graph reducer.

---

## 5. Data model

The graph is modelled relationally, not in a graph database:

- `farmers`, `farms`
- `trust_sources`, `institutions`, `social_groups`, `market_actors`
- link tables: `farmer_trust_source_links`, `farmer_institution_links`, `farmer_social_group_links`, `farmer_market_actor_links`
- `verification_sessions`, `verification_participants`
- signals: `testimonials`, `buyer_testimonials`, `discipline_proxies`, `in_kind_settlement_proofs`, `farm_activity_signals`
- scoring: `score_profiles` (versioned, one current row per farmer), `score_components`
- `loans`, `verifier_credibility`, `fraud_flags`, `audit_logs`

Key relationships:

```text
Farmer -> Farm
Farmer -> TrustSource      (community testimony)
Farmer -> MarketActor      (buyer relationship)
Farmer -> SocialGroup      (discipline proxy)
Farmer -> Institution
Farmer -> VerificationSession -> VerificationParticipant -> signal rows
Farmer -> ScoreProfile -> ScoreComponent
Farmer -> Loan
```

The schema is created with Alembic. Least-privilege database roles live in `backend/db/roles.sql`; the scoring role can read a `farmers_scoring_safe` view that excludes gender.

---

## 6. Scoring

The implementation follows the provisional scorecard in `scoring.md`.

### Response scale

Subjective responses use a forced 4-point scale with no neutral midpoint:

| Rating | Meaning | Score value |
| --- | --- | --- |
| 1 | Poor / unreliable | 0 |
| 2 | Below average | 33.3 |
| 3 | Above average | 66.7 |
| 4 | Excellent / very reliable | 100 |

A testimony is excluded when `personal_knowledge_flag` is false.

### Character axis

```
contribution = base_category_weight x credibility_multiplier x score_value
```

- Base weights are category constants (for example Chief = 4.0, Neighbour = 1.0).
- New verifiers start with credibility 1.0; the multiplier is stored per verifier.
- Multiple testimonies are pooled as a weighted average.
- Testimony from three or more distinct categories receives a 1.1x diversity bonus.

Available components are renormalised:

| Component | Weight |
| --- | ---: |
| Discipline proxy | 0.35 |
| Buyer relationship | 0.30 |
| In-kind settlement | 0.20 |
| Community testimony | 0.15 |

### Capacity axis

Capacity comes from the latest farm activity signal (cultivation continuity). It must already be per-hectare normalised; raw acreage is never scored. When no reading exists, capacity is `null` and the final score uses character only.

### Final score and decisions

```
final = character                                  (capacity unavailable)
final = 0.60 x character + 0.40 x capacity         (capacity available)
```

| Final score | Decision | Recommendation |
| --- | --- | --- |
| >= 75 | `ELIGIBLE` | `APPROVE_LEVEL_2`, KES 5,000 |
| >= 60 | `ELIGIBLE` | `APPROVE_LEVEL_1`, KES 3,000 |
| >= 45 | `REVIEW_REQUIRED` | Manual review |
| < 45 | `DECLINE` | Insufficient community trust |

Bias rules are enforced in the design and reflected in the data model: gender, ethnicity, religion, disability, age, and raw acreage are not scoring inputs. The analytics API reports the excluded-input list and acreage/score correlation for review.

---

## 7. API surface

Base URL: `http://localhost:8000`. Interactive docs: `/docs`.

### Health and analytics

| Method | Path |
| --- | --- |
| `GET` | `/health` |
| `GET` | `/api/stats/overview` |

### Farmers, farms, and network

| Method | Path |
| --- | --- |
| `POST` | `/api/farmers` |
| `GET` | `/api/farmers` |
| `GET` | `/api/farmers/{farmer_id}` |
| `POST` | `/api/farmers/{farmer_id}/farm` |
| `GET` | `/api/farmers/{farmer_id}/network` |
| `POST` | `/api/farmers/{farmer_id}/link-trust-source` |
| `POST` | `/api/farmers/{farmer_id}/link-institution` |
| `POST` | `/api/farmers/{farmer_id}/link-social-group` |
| `POST` | `/api/farmers/{farmer_id}/link-market-actor` |
| `POST` | `/api/farmers/{farmer_id}/inkind-settlement` |

### Trust entities

| Method | Path |
| --- | --- |
| `POST` | `/api/trust/sources` |
| `POST` | `/api/trust/institutions` |
| `POST` | `/api/trust/social-groups` |
| `POST` | `/api/trust/market-actors` |

### Verification and scoring

| Method | Path |
| --- | --- |
| `POST` | `/api/verify/start` |
| `POST` | `/api/verify/{session_id}/respond/{participant_id}` |
| `POST` | `/api/verify/{session_id}/timeout/{participant_id}` |
| `GET` | `/api/verify/{session_id}/status` |
| `GET` | `/api/verify/{session_id}/result` |
| `GET` | `/api/verify/{session_id}/breakdown` |
| `GET` | `/api/verify/{session_id}/explanation` |

The explanation route is an LLM call and can take about 60 seconds. It accepts `mode=expert|farmer` and `language=<name>`.

### Loans

| Method | Path |
| --- | --- |
| `POST` | `/api/loans` |
| `GET` | `/api/loans?farmer_id=&status=` |
| `POST` | `/api/loans/{loan_id}/disburse` |
| `POST` | `/api/loans/{loan_id}/repay` |
| `POST` | `/api/loans/{loan_id}/default` |

Errors use `{"detail": "..."}` or a validation list. Duplicate or invalid state returns 409, validation 422, missing resources 404. Request bodies reject unknown fields.

---

## 8. Frontend routes

| Route | Screen |
| --- | --- |
| `/` | Portfolio: metrics, score bands, searchable farmer list |
| `/ui` | Analytics dashboard: loan book, decision mix, fairness, recent cases |
| `/case/new` | New six-step assessment |
| `/case/:caseId` | Resume an assessment from the network endpoint |
| `/replay` | Recorded Grace Wanjiku walkthrough with score and breakdown |

The case workflow is:

1. Farmer
2. Farm
3. Trust network
4. Verification
5. Score and explanation
6. Loan

---

## 9. Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- A Neon PostgreSQL database (or any PostgreSQL 15+ instance)
- Optional: a Groq API key for explanations
- Optional: a Google Earth Engine service account for farm activity

### 1. Clone

```bash
git clone https://github.com/Deo-Siatah/CodeGreen-kenyaAiChallenge.git
cd CodeGreen-kenyaAiChallenge
```

### 2. Backend

```bash
cd backend
cp .env.example .env
# edit .env with your database and provider credentials
uv sync
uv run alembic upgrade head
uv run uvicorn main:app --reload
```

The API runs at `http://localhost:8000`. Run `uv run pytest` for tests.

To load demo farmers and linked signals:

```bash
uv run python scripts/seed_demo.py
```

Apply the least-privilege roles after the schema exists:

```bash
psql "$DATABASE_URL_DIRECT" -f db/views.sql
psql "$DATABASE_URL_DIRECT" -f db/roles.sql
```

Migrations use `DATABASE_URL_DIRECT`, never the pooled URL. To target a disposable branch explicitly:

```bash
uv run alembic -x dburl="$TEST_DATABASE_URL_DIRECT" upgrade head
```

### 3. Frontend

```bash
cd ../frontend
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_URL` to the backend origin.

### 4. Verification commands

```bash
cd frontend
npm run check    # typecheck + lint + production build + unit tests
npm run e2e      # Playwright; requires a TEST database branch and running servers
```

From `backend`:

```bash
uv run pytest tests/unit
uv run ruff check .
```

Never point e2e or integration tests at the main database branch.

---

## 10. Environment variables

Create `backend/.env` from `backend/.env.example`.

| Variable | Required | Purpose |
| --- | --- | --- |
| `APP_NAME` | Yes | Application name |
| `DATABASE_URL_POOLED` | Yes | PgBouncer/Neon pooled URL used by the app |
| `DATABASE_URL_DIRECT` | Yes | Direct URL used by Alembic and migrations |
| `DB_SCORING_ROLE` | No | Least-privilege role, default `app_scoring` |
| `DB_ANALYTICS_ROLE` | No | Analytics role, default `app_analytics` |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins, default `http://localhost:5173` |
| `FARM_ACTIVITY_PROVIDER` | No | `null` (default) or `earth_engine` |
| `EARTH_ENGINE_SERVICE_ACCOUNT_JSON` | Yes | Path to the service-account file; validated when Earth Engine is enabled |
| `GROQ_API_KEY` | For explanations | Groq key used by the active provider |
| `GROQ_MODEL` | No | Default `openai/gpt-oss-120b` |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Currently yes | Retained settings; Gemini provider is disabled in code |
| `DEFAULT_EXPLANATION_MODE` | No | `farmer` (default) or `expert` |
| `BACKEND_URL` | Yes | Public backend origin |
| `USSD_WEBHOOK_URL` / `SMS_WEBHOOK_URL` | Yes | Reserved callback URLs |
| `AFRICASTALKING_API_KEY` / `AFRICASTALKING_USERNAME` | Yes | Africa's Talking credentials retained for SMS work |
| `TEST_DATABASE_URL_DIRECT` | Tests only | Direct URL to a disposable test branch |
| `NEO4J_*` | Currently yes | Deprecated; retained until the migration is fully verified |

Frontend `frontend/.env`:

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | Backend origin, default `http://localhost:8000` |

Never commit `.env` files or real credentials.

---

## 11. Project structure

```text
CodeGreen-kenyaAiChallenge/
├── backend/
│   ├── api/                  # FastAPI routers: section13 (main API), stats, ai, trust
│   ├── core/                 # Settings and async database engines
│   ├── db/                   # Role grants and scoring-safe view SQL
│   ├── migrations/           # Alembic environment and versions
│   ├── models/               # SQLAlchemy models (farmers, trust, signals, scoring, loans)
│   ├── repositories/         # Query and persistence layer
│   ├── schemas/              # Pydantic request/response contracts
│   ├── services/             # Scoring, verification, trust, loans, stats, explainability
│   ├── scripts/              # Demo seed and provider smoke scripts
│   ├── tests/                # Unit and integration tests
│   ├── main.py               # App entrypoint, lifespan, router registration
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── scripts/              # Replay recorder
│   ├── src/
│   │   ├── api/              # axios client, endpoints, Zod schemas, generated OpenAPI types
│   │   ├── app/              # Case layout, steps, stepper, evidence ledger
│   │   ├── components/       # Product header, shadcn/ui primitives
│   │   ├── domain/graph/     # Pure reducer, hydrate, selectors, ring layout
│   │   ├── e2e/              # Playwright fixtures and specs
│   │   ├── features/         # portfolio, dashboard, graph, ussd simulator
│   │   ├── i18n/             # English/Kiswahili dictionary and toggles
│   │   ├── replay/           # Recorded replay schema and Grace Wanjiku data
│   │   ├── styles/           # Design tokens
│   │   ├── test/             # MSW server and fixtures
│   │   └── theme/            # Light/dark provider and toggle
│   ├── docs/                 # Legacy UI inventory
│   ├── playwright.config.ts
│   └── package.json
├── AGENTS.md                 # Engineering rules for contributors/agents
├── scoring.md                # Data and scoring design
├── setup.md                  # Original MVP implementation plan
├── CODEBASE_SUMMARY.md       # Historical codebase audit
└── README.md
```

---

## 12. Current status and limitations

**Working**

- Farmer, farm, trust-network, verification, scoring, explanation, loan, and analytics endpoints
- Versioned score profiles with component-level breakdowns
- Portfolio, analytics, six-step case, and replay screens
- Unit and integration tests for the current API contracts

**Not yet live**

- **USSD/SMS callback routes.** The frontend includes a USSD simulator and the Africa's Talking settings/SMS helpers remain, but live callback endpoints are not registered in the current app.
- **Automatic outreach and timeout scheduler.** Verification participants are snapshotted and can be responded to or timed out through the API; there is no background worker.
- **Gemini.** The active explanation provider is Groq. The Gemini provider is commented out.
- **Earth Engine by default.** `FARM_ACTIVITY_PROVIDER=null` means capacity is unavailable until a real provider is configured.
- **Authentication.** There is no auth layer yet; the API client keeps a single interceptor seam for it.
- **Backend test collection.** Focused unit and API tests pass, but the full collection still includes legacy modules (`backend/tests.py` and an obsolete Gemini provider test) that need cleanup before `uv run pytest` is a clean signal.

---

## 13. Team

**Team Code Green**

- **Deo Siatah** — Lead Software Engineer / Graph Architecture
- **Laura Shaviya** — Frontend Developer / UX Lead
- **Dancan Mibei** — Database Administrator / Scoring Logic
- **Rebeca Agai** — AI Prompt Engineer / QA Specialist
- **Said Kombe** — Systems Integrator / Telecom Operations

---

## 14. Acknowledgments

- **AFRACA** for the "Invisible Farmer" challenge brief
- **Mercy Corps AgriFin** for the track and mentoring
- **Neon** for PostgreSQL hosting
- **Groq** for the current explanation provider
- **Google Earth Engine** for satellite farm-activity data
