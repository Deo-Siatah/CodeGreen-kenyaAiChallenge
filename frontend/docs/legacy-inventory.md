# Legacy Frontend Inventory

This document inventories the existing frontend components before cleanup. The legacy UI was a Neo4j-era dashboard with mock fallbacks.

## Inventory Table

| File | What it did | Mock data usage | Verdict |
|------|-------------|----------------|---------|
| `App.tsx` | Main application with tab navigation (dashboard, farmers, testifiers) | Uses MOCK_VERIFICATION_RESULTS for mock fallbacks | REPLACE |
| `App.css` | Global styles with Tailwind CSS imports and custom CSS classes | No mock data | PORT (styles needed) |
| `main.tsx` | React app entry point | No mock data | PORT (needed for build) |
| `index.css` | Tailwind CSS import | No mock data | PORT (needed for build) |
| `components/Dashboard.tsx` | Dashboard with metrics, charts, and farmer cards | Uses mock data for display; has hard-coded 97.4% repayment rate | REPLACE |
| `components/FarmerList.tsx` | List of farmers with search/filter functionality | Uses mock data for farmer list | REPLACE |
| `components/FarmerDetail.tsx` | Detailed view of individual farmer with verification info and Kiswahili toggle | Uses mock data for verification; has Kiswahili label toggle | PORT (Kiswahili toggle → language selector in U6) |
| `components/TestifiersView.tsx` | View of testifiers/verifiers with credibility metrics | Always uses mock data (MOCK_TESTIFIERS) | PORT (testifier concept → verifier credibility rings in U7) |
| `services/api.ts` | API service with URL guessing from localStorage and hosted fallback | Heavy mock data usage (MOCK_FARMERS, MOCK_TESTIFIERS, etc.) | REPLACE (API logic needs to be rewritten) |
| `assets/` | Static assets (hero.png, react.svg, vite.svg) | No mock data | PORT (if assets are still referenced) |

## Key Findings

### Mock Data Usage
- Heavy reliance on mock data throughout the application
- MOCK_FARMERS, MOCK_TESTIFIERS, MOCK_VERIFICATION_RESULTS, MOCK_VERIFICATION_LOGS
- Mock data serves as fallback when API is unavailable

### Hard-coded Values
- 97.4% repayment rate hard-coded in Dashboard.tsx
- URL guessing logic in api.ts that falls back to localhost:8000 or hosted service

### Kiswahili Implementation
- Language toggle in FarmerDetail.tsx only swaps labels
- Limited to English/Swahili label switching without real translation

### Testifier Audit
- Testifier view always uses mock data
- No real backend integration for testifier credibility

## PORT Ideas (to be kept and enhanced)

1. **Kiswahili Toggle** → Becomes explanation language selector in U6
2. **Testifier Concept** → Becomes verifier credibility rings in U7
3. **Basic Styling** → Tailwind CSS and custom styles to be preserved
4. **Static Assets** → Hero images and icons that are still referenced

## PORT Ideas Implementation Plan

| PORT Idea | Implementation Target | Notes |
|-----------|----------------------|-------|
| Kiswahili Toggle | U6: Explanation language selector | Language toggle from FarmerDetail.tsx will be enhanced to support proper translations |
| Testifier Concept | U7: Verifier credibility rings | Testifier credibility metrics from TestifiersView.tsx will be adapted for new system |

## REPLACE (new UI covers this functionality)

1. Dashboard layout and metrics display
2. Farmer list and detail views
3. API service with proper URL configuration
4. Mock data fallback system

## DROP (legacy functionality no longer needed)

1. Neo4j-era patterns and integrations
2. Hard-coded statistics
3. localStorage URL guessing
4. Mock data as primary data source