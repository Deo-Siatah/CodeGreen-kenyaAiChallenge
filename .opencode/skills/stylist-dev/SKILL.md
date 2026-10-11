---
name: stylist-dev
description: Use when fixing bugs, reviewing changes, or doing maintenance in the CodeGreen-kenyaAiChallenge project. Invoked with /stylist-dev and a problem description.
---

# CodeGreen Kenya AI Challenge - Development Assistant

## Project Overview
This is Hifadhi, an alternative agricultural credit scoring platform that maps community trust signals into a Neo4j graph database. Built for AFRACA's "Invisible Farmer" brief using FastAPI backend and React frontend.

## Critical Architecture Notes

### Database Constraints
- **NEO4J initialization required**: Run `python scripts/init_graph.py` before starting backend
- **Module-level singletons**: Database engines are created at import time, not per-test
- **Asyncpg connections**: Bound to the event loop - use `asyncio_default_test_loop_scope = "session"`

### Weighting System
- **Active file**: `services/weighting.py` (imported in `scoring_service.py:18`)
- **Legacy files**: `weighting_old.py`, `weighting_backup.py` (do not use)
- **Separate service**: `weighting_service.py` for trust scoring (different purpose)

### Testing Configuration
- **pytest async mode**: `asyncio_mode = "auto"` and `asyncio_default_test_loop_scope = "session"`
- **Import paths**: Tests can import directly from modules (e.g., `from services.weighting import ...`)
- **Python path**: Configured to make `backend/` the import root

### Frontend Configuration
- **Backend URL**: Configured via browser's local storage (Settings menu ⚙️)
- **Hot-swapping**: Supports ngrok/localtunnel URLs during testing
- **Build command**: `npm run build` includes TypeScript compilation

## Environment Requirements

### Mandatory Environment Variables (backend/.env)
```
NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
AFRICASTALKING_API_KEY, AFRICASTALKING_USERNAME
GEMINI_API_KEY, GROQ_API_KEY
BACKEND_URL, USSD_WEBHOOK_URL, SMS_WEBHOOK_URL
APP_NAME
```

### Critical Setup Order
1. Create virtual environment: `python -m venv .venv`
2. Install dependencies: `pip install -e .`
3. Initialize Neo4j: `python scripts/init_graph.py`
4. Start backend: `uvicorn main:app --reload`

## Development Guardrails

### Database Operations
- **Never modify** graph constraints/indexes without running `scripts/init_graph.py`
- **Use** `core.database.verify_db_connection()` to test connections
- **Async operations only**: All database calls must be async

### API Integration
- **SMS/USSD**: Only through Africa's Talking SDK
- **AI explanations**: Only through Gemini API
- **Farm activity**: Optional Earth Engine integration (default: null)

### Testing Rules
- **Never run tests without proper database setup**
- **Use pytest with async mode** - no need for @pytest.mark.asyncio decorators
- **Test files**: Must be in `tests/` directory
- **Single test**: `pytest -xvs tests/unit/services/test_weighting.py::test_response_scale_maps_four_point_scale`

### File Structure Constraints
- **Backend services**: Keep pure scoring functions in `weighting.py` (no database imports)
- **Frontend backend URL**: Must be configured via browser local storage for testing
- **Configuration**: Settings in `core/config.py` use pydantic-settings

### Common Pitfalls to Avoid
1. **Never** change active weighting file without updating imports
2. **Always** restart backend after Neo4j schema changes
3. **Never** use `weighting_old.py` or `weighting_backup.py` in active code
4. **Always** run `python scripts/init_graph.py` before starting backend
5. **Never** forget to activate virtual environment before running commands

## Debugging Commands

### Database Issues
```bash
# Test connection
cd backend && python -c "from core.database import verify_db_connection; verify_db_connection()"

# Check constraints
cd backend && cypher-shell -u $NEO4J_USERNAME -p $NEO4J_PASSWORD "SHOW CONSTRAINTS"
```

### Testing Issues
```bash
# Run specific test with verbose output
pytest -xvs tests/unit/services/test_weighting.py::test_response_scale_maps_four_point_scale

# Run all tests with coverage
pytest --cov=services
```

### Environment Issues
```bash
# Validate configuration
cd backend && python -c "from core.config import validate_configuration; validate_configuration()"
```

## Weighting System Debugging
When working with scoring logic:
- Check `BASE_CATEGORY_WEIGHTS` in `services/weighting.py`
- Verify `response_scale_to_value()` function maps 1-4 to 0-100 correctly
- Test `pool_testimonies()` and `combine_character_components()` functions

## Africa's Talking Integration
- Sandbox mode: Use `sandbox` as username for testing
- Webhook URLs: Must be publicly accessible for SMS/USSD callbacks
- USSD: Requires standard shortcode provisioning for production

## AI Integration
- **Gemini model**: `gemini-3.5-flash` (configurable in `core/config.py`)
- **Explanation modes**: "expert" or "farmer" (default: "farmer")
- **Groq fallback**: `openai/gpt-oss-120b` for alternative AI processing

## Frontend Development
- **React 19** with TypeScript
- **Vite** build system
- **TailwindCSS** v4 for styling
- **Hot reload** enabled during development

## Common Fix Patterns

### Database Schema Changes
1. Update `graph/schema.py`
2. Run `python scripts/init_graph.py`
3. Update affected Cypher queries
4. Test with `pytest tests/unit/services/test_*.py`

### Scoring Logic Changes
1. Modify `services/weighting.py`
2. Update corresponding tests
3. Run `pytest tests/unit/services/test_weighting.py`
4. Verify scoring results in Neo4j

### API Changes
1. Update route in `api/` directory
2. Add/update Pydantic schemas in `schemas/`
3. Update frontend service calls
4. Test with curl or frontend UI

## Emergency Procedures

### Database Connection Issues
1. Check Neo4j Aura instance status
2. Verify `.env` credentials
3. Test with `cypher-shell` command
4. Reinitialize if needed: `python scripts/init_graph.py`

### Backend Won't Start
1. Check all environment variables
2. Verify Python dependencies: `pip list`
3. Check database connection: `verify_db_connection()`
4. Look for import errors in `main.py`

### Frontend Build Fails
1. Check Node.js version (requires 18+)
2. Run `npm install` to refresh dependencies
3. Verify TypeScript types: `npm run build`
4. Check backend URL configuration in browser storage

## Performance Notes
- Neo4j queries should use indexes for performance
- Async operations prevent blocking the event loop
- Large graph operations may require optimization
- Gemini API calls have rate limits