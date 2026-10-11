# Hifadhi Phase 2.0 — Data & Scoring Design

**Status:** Draft for team review
**Scope:** How we obtain, verify, classify, and score farmer signals — and how this is demoed live.
**Non-goal (for now):** Voice/IVR delivery, fraud-ring detection algorithms, UI. Those build on top of this once the data layer is solid.

---

## 1. Data Acquisition — how we actually get each signal

Every signal has a different collection mechanism. We don't collect "trust" in the abstract — we collect specific, dated, structured facts from specific people or systems.

| Signal | Source | Channel | Trigger | Built today? |
|---|---|---|---|---|
| Community testimony | Chief / elder / school head / religious leader (`TrustSource`) | USSD prompt via Africa's Talking, tied to their phone number | Loan officer starts a `VerificationSession` | Yes — binary YES/NO/UNSURE only |
| Buyer relationship | Agrovet / aggregator / buyer (`MarketActor`) | USSD/SMS prompt to the buyer's registered phone | Same session | Schema exists (`BuyerTestimonial`), not wired into score |
| Discipline proxy | Chama/SACCO officer (`SocialGroup` contact) | USSD/SMS prompt to the group's registered contact | Same session | Schema exists (`SocialGroup`), not wired into score |
| In-kind settlement | Counterparty who received the in-kind payment | USSD/SMS confirmation, or farmer self-report cross-checked by counterparty | Farmer/officer submits a claim | Schema exists (`InKindSettlementProof`), not wired into score |
| Farm activity (capacity axis — new) | Satellite (Sentinel-2 via Google Earth Engine, free tier) | Automated pull keyed on `Farm.latitude/longitude` | On `Farm` creation, then on a schedule (e.g. monthly) | Not built — new for Phase 2.0 |
| Mobile money (stretch, not MVP) | M-Pesa via Safaricom Daraja | API, requires farmer consent + partner integration | Post-MVP | Not built |

**MVP acquisition rule:** every human-sourced signal above (all except farm activity) must move from a binary YES/NO/UNSURE response to a **structured follow-up** that captures a number and a date wherever possible — e.g. a Chama chair isn't just asked "is this farmer disciplined?" (a character judgment call), but "how many consecutive contribution cycles has this farmer completed, and when was the last one?" This is the single change that makes discipline and buyer signals *specific* rather than *subjective* — see §3 for why that matters for scoring.

Farm activity requires no human respondent at all — it's the one signal we can obtain and verify without waiting on anyone to answer a phone, which makes it valuable both for score robustness and for live demos (§4).

---

## 1.5 Data Layer — Postgres instead of Neo4j

**Decision: move off Neo4j to Postgres.** Aura Free pausing/expiring has already cost us time once, and our actual traversal needs don't require a native graph engine.

**Schema:**

```sql
CREATE TABLE nodes (
  id UUID PRIMARY KEY,
  label TEXT NOT NULL,           -- Farmer, TrustSource, Farm, MarketActor, SocialGroup, ...
  properties JSONB NOT NULL
);

CREATE TABLE edges (
  source_id UUID REFERENCES nodes(id),
  target_id UUID REFERENCES nodes(id),
  rel_type TEXT NOT NULL,        -- VERIFIED_BY, OWNS, MEMBER_OF, SELLS_TO, ...
  properties JSONB,
  PRIMARY KEY (source_id, target_id, rel_type)
);

CREATE INDEX idx_edges_source ON edges (source_id);
CREATE INDEX idx_edges_target ON edges (target_id);
CREATE INDEX idx_nodes_label ON nodes (label);
```

**Why this holds up at our scale:**
- All primary traversals (`Farmer → TrustSource`, `Farmer → MarketActor`, `Farmer → SocialGroup`, `Farmer → Farm`) are 1-hop.
- Fraud-pattern queries (reciprocal endorsement loops, verifier fan-out — see §5) are 2-hop at most, expressible as self-joins or a shallow recursive CTE. Cypher's variable-length path syntax isn't needed until traversal depth is unbounded, which nothing here requires.
- One instance holds the graph tables *and* `VerificationSession`/`FinancialSignal`/`ScoreProfile` data — no split infrastructure, no second system that can independently fall over.
- Free tier (Neon or Supabase) has no pause/expiry behavior — this is the actual problem we're solving, not just a preference.

**Trade-off, stated plainly:** Cypher reads more naturally for graph-shaped queries than the equivalent SQL joins. That's an ergonomics cost, not a capability gap, and it's worth paying given the reliability we get back.

**Migration order:** `backend/graph/schema.py` (constraints/indexes) → SQL migration; `backend/repositories/` (Cypher queries) → SQLAlchemy/`asyncpg`; multi-hop fraud queries move into a new `services/graph_analytics.py`, optionally using NetworkX in-memory for the heavier structural checks (dense subgraph detection, clustering coefficient) once the relevant subgraph is loaded.

---

## 2. Classification — do we need ML, and how do connections/signals get verified?

### 2.1 No ML for the score itself, at this stage — and this is a deliberate choice, not a shortcut

We don't have outcome data yet (no completed loan cycles to say "this combination of signals led to repayment or default"). Training or even hand-tuning a classifier against nothing is worse than not having one — it would produce a model that looks sophisticated but is arbitrary, and arbitrary-but-opaque is exactly the failure mode we're positioning against (see the loan-officer-override case study in `/areas/agriforesight-hifadhi.md`... — a farmer denied by a model that couldn't say why).

**MVP approach: a documented, weighted scorecard** (deterministic, auditable, versionable) — not a black box. Weights are asserted from the literature and domain reasoning (Juhudi Kilimo/LenddoEFL, MkulimaScore360, Oliver Wyman's data-quality criteria), explicitly labeled as *provisional pending calibration*, and every score ships with the full breakdown of what produced it.

**Where a model earns its place later:** once we have real repayment outcomes (even 50-100 completed loan cycles), a logistic regression over the same features — not a neural net — is the right upgrade path. Logistic regression keeps per-feature coefficients that are directly explainable ("this factor added 8 points, this one subtracted 3"), unlike a tree ensemble or neural net. This is a Phase 3 decision, not Phase 2.0.

### 2.2 How connections get established

At MVP, graph edges (`Farmer-VERIFIED_BY->TrustSource`, `Farmer-SELLS_TO->MarketActor`, etc.) are created by the loan officer during onboarding, not inferred by any model. A human vouches for the relationship's existence before the system ever contacts anyone. This matters for fraud resistance too — the officer is a first checkpoint before the graph layer gets a chance to do structural fraud analysis later.

### 2.3 How signals get verified

Verification happens on two levels:

1. **Identity-level**: a testimony/response is only accepted if it comes from the phone number already on record for that `TrustSource`/`MarketActor`/`SocialGroup` contact — Africa's Talking ties the USSD/SMS session to a specific MSISDN, so we know the response genuinely originated from the registered respondent, not an arbitrary number.
2. **Cross-corroboration** (design target, not yet built): a discipline or buyer claim carries more weight when more than one independent source confirms it — e.g. both the Chama chair and one ordinary member report consistent contribution history. Single-source claims aren't rejected, just weighted lower than corroborated ones. This is a scoring-time weighting rule, not a new data structure.
3. **Third-party verification** (farm activity): satellite data is inherently third-party — no one on the farmer's side can directly manipulate what Earth Engine observes, which is why it's a structurally different (and structurally more fraud-resistant) signal than testimony.

---

## 3. Score Conversion — explainable, bias-resistant, adaptive

### 3.1 Two-axis architecture

Rather than one blended number, the score is built from two **orthogonal** sub-scores that get combined at the end. This split is the core design decision of Phase 2.0:

- **Character axis** (0-100): community testimony, discipline proxies, buyer relationship consistency, in-kind settlement history. Answers "does this person behave in ways consistent with repaying?"
- **Capacity axis** (0-100): farm activity consistency (NDVI-derived cultivation continuity, normalized per hectare), buyer transaction volume where available. Answers "can this farm plausibly generate the income to repay?"

**Why split them:** they answer genuinely different questions, and blending them into one number from the start hides *why* a score is what it is. A farmer with strong community standing but an inactive farm, and a farmer with a thriving farm but no community ties, should not land on the same score for the same reason — the breakdown has to survive being looked at, not just the final number.

Within the character axis, sub-weights should be defensible, not equal:

| Component | Provisional weight | Rationale |
|---|---|---|
| Discipline proxies (dated, numeric) | Highest | Most specific — real behavioral time-series, per Oliver Wyman's criteria |
| Buyer relationship (dated, transactional) | High | Specific if captured as transaction records, not narrative |
| In-kind settlement | Moderate | Real but low-coverage — bonus signal, not core |
| Community testimony | Lowest of the four, but gates the others | Corroborating/qualifying signal — confirms the farmer is who they claim to be and is in good standing, rather than driving the score directly |

This inverts the current implementation's default (which only uses testimony) — a deliberate, documented change, not an oversight.

### 3.2 Explainability requirement, structurally enforced

The scoring function must return a **structured breakdown object**, not a float:

```
{
  "final_score": 68,
  "character_score": 71,
  "capacity_score": 63,
  "character_breakdown": [
    {"component": "discipline_proxy", "raw_value": "5 consecutive Chama cycles",
     "contribution": 24, "weight": 0.35},
    {"component": "buyer_relationship", "raw_value": "18-month relationship, 40kg/week avg",
     "contribution": 20, "weight": 0.30},
    ...
  ],
  "capacity_breakdown": [
    {"component": "cultivation_continuity", "raw_value": "consistent NDVI cycles, 3 seasons",
     "contribution": 40, "weight": 0.6},
    ...
  ]
}
```

This isn't a nice-to-have for the AI explanation layer — it's what makes Gemini's narration factual instead of a paraphrase of a number it can't actually account for. The explanation service should never receive just `score: 68`.

### 3.3 Bias-resistance checklist — concrete rules, not a values statement

- **Never score raw farm acreage.** Normalize every farm-derived metric per hectare, so a well-tended half-acre scores as well as a well-tended five-acre plot. Raw acreage correlates with existing wealth/privilege — scoring it directly re-encodes the same exclusion the product exists to remove.
- **Never use gender, ethnicity, religion, or disability status as scoring inputs**, even indirectly via a proxy field. (Worth an explicit code-review checklist item, not just a design intention.)
- **Weight subjective testimony lower than dated transactional/behavioral data** — for the same specificity reason as above.
- **Watch "years known" as a verifier-relationship field.** Weighting it heavily structurally penalizes farmers who are new to an area, and this correlates with the same populations (young farmers, women who've recently married into a community) the product is meant to include. Cap its influence or exclude it from the weight formula entirely; capture it for context, not for scoring.
- **Log every score's full breakdown**, even at MVP. This is what makes a fairness audit possible later ("do women systematically score lower on component X, and why") — you can't investigate what you didn't record.

### 3.4 Adaptive, not frozen

A score is not computed once and left alone. Model it as a versioned `ScoreProfile` (the schema already has this label) that gets **recomputed**, with history retained, whenever:

- A new `VerificationSession` completes
- A new `FinancialSignal` or farm NDVI reading arrives
- A `Loan` resolves (repaid or defaulted) — this is the one event that should eventually feed back into recalibrating the weights themselves, once enough of them exist

Store each computation as a new `ScoreProfile` version rather than overwriting the previous one. This gives you, for free: an audit trail for a loan officer or judge to see how a score moved, and the raw dataset a future logistic regression will need to calibrate against real outcomes.

---

## 4. Phase 2.0 Implementation — live, judge-testable demo

Goal: a judge (or anyone) can enter a farmer's details live, watch the trust network and farm data connect, see the score build up with its breakdown, and read a plain-language explanation — all in one sitting, using real computation, not mocked output.

**Proposed flow:**

1. **Create farmer + farm live** — officer/judge enters basic details plus the farm's location (can be a real pin on a map, or a known demo location).
2. **Register verifiers live** — add a chief, a buyer, a Chama contact. UI shows the graph forming in real time as each is added (this is a strong visual moment for a demo — worth prioritizing in the UI work that follows this doc).
3. **Trigger farm activity pull** — call Google Earth Engine live with the farm's coordinates. This is genuinely real data, not simulated, and it returns fast enough to work in a live demo — a strong credibility moment because nothing here is staged.
4. **Trigger verification session** — for a live demo, waiting on real chiefs to answer isn't practical. Two honest options, not mutually exclusive:
   - **Judge plays multiple roles**: the judge's own phone receives the USSD/SMS prompts for each verifier role in sequence, so they experience the actual respondent-facing flow.
   - **Demo-mode session**: a flag on `VerificationSession` that shortens timeout windows for demo purposes, but still runs the real scoring/session code path — this is different from the current frontend's hardcoded mock data, which we should retire rather than extend. Sped-up-but-real beats fast-but-fake.
5. **Score computes and displays breakdown** — character axis, capacity axis, combined score, full component list, all visible.
6. **Explanation generates** — Gemini receives the structured breakdown (§3.2) and produces plain-language reasoning, shown in the UI in real time.
7. *(Later phase, not now)* — voice narration of the same explanation in Kiswahili, using the same structured breakdown as its input so the spoken explanation is exactly as factual as the written one.

**What this requires before it's demoable**, in order:
1. Extend `ScoringService` to implement the two-axis model in §3.1, returning the breakdown object in §3.2
2. Wire `BuyerTestimonial`, discipline data (`SocialGroup`), and `InKindSettlementProof` into that computation (currently unused)
3. Build the Earth Engine integration for farm activity (new)
4. Fix live verifier outreach (`start_verification` currently doesn't send outreach SMS — already flagged as a gap)
5. Fix the `/ai` explainability route (already flagged as broken — method name mismatch)
6. Frontend: real-time graph visualization + breakdown display, replacing the current mock-session-ID live-mode hack

---

## 5. Integrity — preventing hollow/collusive vouching

The core vulnerability: right now, endorsement weight is a **static category constant** (`Chief = 4`, `Neighbor = 1`, hardcoded in `weighting_service.py`). It doesn't matter whether a specific chief has a track record of vouching for people who later defaulted, or is rubber-stamping every friend who asks — the system currently can't tell the difference. No single fix below closes this alone; together they raise the cost of gaming the system well above the cost of being honest.

1. **Verifier credibility becomes a tracked, evolving score — not a fixed category weight.** Every time a loan tied to a given verifier's endorsement resolves (repaid or defaulted), it feeds back into that verifier's credibility. A "Chief" who's endorsed five people, three of whom defaulted, should carry less weight than one whose endorsees have a clean record, regardless of title. This is the single most powerful anti-collusion mechanism — it gives every verifier real skin in the game, so blanket positive vouching becomes self-defeating over time.
   - **Build note:** the frontend's `TestifiersView` component already displays verifier credibility and default-rate flags — it's currently permanently mock because no backend endpoint feeds it. The UI instinct was already right; wiring this up is now a concrete, prioritized build item, not a future nice-to-have.

2. **Require cross-corroboration, not a single yes.** The character axis already spans four independent source types (testimony, buyer, discipline, settlement) — collusion is meaningfully harder when a farmer needs to compromise several unrelated people/institutions rather than one friendly chief. Within a single source type, prefer two respondents over one where feasible (e.g. the Chama chair *and* one ordinary member).

3. **Ask falsifiable questions, not sentiment.** "How many consecutive Chama cycles has this farmer completed, and when was the last one?" is harder to fake convincingly than a YES/NO character judgment, and is checkable against the group's own separate records if that access ever exists. A specific false claim is exposed in a way a vague endorsement never is — this is the same structural-data change already required in §1 for scoring specificity, doing double duty here.

4. **Break the "farmer picks their own cheerleaders" dynamic.** If verifiers are entirely self-nominated by the farmer at onboarding, they'll naturally skew toward people inclined to say yes. At least one verifier per session should be sourced independently — by the loan officer, or sampled from the farmer's registered institution/SocialGroup rather than hand-picked by the farmer.

5. **Structural graph analysis flags patterns, not individual lies.** Reciprocal-only endorsement loops, one verifier vouching for an implausible number of farmers in a short window, synchronized submission timing — these are review flags for a loan officer, not automatic declines. This is a detection layer, not a verdict.

6. **This never fully closes without a human-in-the-loop audit.** A genuinely organized fraud ring will beat any single layer above. A small random sample of approved cases getting a real phone call or field check is the honest backstop, and it's worth stating this plainly in the pitch rather than implying the system is fraud-proof — no credit system anywhere actually is.

### 3.5 Testimony pooling and the response scale

**Response scale: 4-point forced choice, no neutral midpoint.**

```
1 = Poor / Unreliable
2 = Below average
3 = Above average
4 = Excellent / Very reliable

+ separate flag: personal_knowledge_flag = false when the respondent doesn't know
  the farmer well enough to judge — excluded from the score contribution entirely,
  never treated as a neutral middle value
```

This replaces the old YES=100/UNSURE=50/NO=0 mapping for *subjective* responses (community testimony, buyer reliability rating). It does **not** apply to discipline proxies (Chama cycles, contribution dates) — those stay as structured numeric facts, not ratings, since they're checkable data rather than opinions. Forced-choice (no exact middle) is a deliberate methodology decision: a scale with a true midpoint invites central-tendency bias, where respondents cluster toward "safe and neutral" rather than committing to a real lean, especially when judging someone they know socially. Forcing a lean produces a sharper, more honest signal.

Mapping to a 0-100 contribution value:

```
score_value = (rating - 1) / 3 × 100
1 → 0     2 → 33.3     3 → 66.7     4 → 100
```

**Per-testimony contribution:**

```
contribution = base_category_weight × credibility_multiplier × score_value
```

- `base_category_weight`: cold-start value by role (Chief = 4, Neighbor = 1, etc.), used before any track record exists.
- `credibility_multiplier`: from `verifier_credibility.credibility_score` — starts neutral (1.0) for a new verifier, drifts up or down as their past endorsees repay or default (§5).
- `score_value`: from the 4-point scale above.

**Pooling multiple testimonies (e.g. 3 neighbors respond):**

```
testimony_score = Σ(contribution_i) / Σ(weight_i)
```

A weighted average, not a sum — adding a 4th agreeing respondent shifts the average only if their answer differs from the existing consensus, so headcount alone can't inflate a score.

**Diversity bonus, applied once at the axis level, not per-testimony:** testimony sourced from 3+ distinct category types (e.g. chief + buyer + Chama chair) multiplies the pooled testimony contribution by a small factor (proposed 1.1×). Testimony from a single category (3 neighbors) earns no bonus — this is the concrete mechanism that makes "get three friends to all vouch for me" structurally weaker than genuine cross-community standing, without complicating the per-testimony formula.

**Disagreement is itself a signal, not noise to average away.** Track variance across a response pool (e.g. 2 respondents say "Excellent," 1 says "Poor") and record it as its own row in `score_components` (`component_name: "testimony_agreement"`) for loan-officer review — a high-disagreement case shouldn't silently resolve to a middling average without a flag.

**Worked example** — 3 neighbors respond: 4, 4, 2 (no credibility history yet, multiplier = 1.0 for all):

```
neighbor 1: 1 × 1.0 × 100.0 = 100.0
neighbor 2: 1 × 1.0 × 100.0 = 100.0
neighbor 3: 1 × 1.0 × 33.3  = 33.3

testimony_score = (100.0+100.0+33.3) / (1+1+1) = 77.8
(no diversity bonus — single category)
```

This becomes one component feeding the character axis (§3.1), alongside buyer/discipline/settlement contributions — never the whole score on its own.

---

## Open questions for the team

- Provisional axis weighting (character vs. capacity split) — proposing 60/40 in favor of character for MVP, since capacity (farm-only) currently has one real signal (NDVI) versus four for character. Revisit once farm signals expand.
- Do we cross-verify discipline/buyer claims with a second source at MVP, or defer to Phase 3 given the added USSD round-trips it requires?
- Confirm: is Earth Engine's free tier (Sentinel-2, 10m resolution, ~5-day revisit) sufficient for our plot sizes, or do we need a paid tier for anything in our farmer sample?