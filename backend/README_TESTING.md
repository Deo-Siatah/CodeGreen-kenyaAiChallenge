# Hifadhi Backend Edge Case Testing Suite

This comprehensive testing suite covers all major edge cases identified in the scoring.md document for the Hifadhi scoring system. The tests are designed to stress-test the backend and ensure proper handling of edge cases.

## Test Scripts Overview

### 0. `test_basic_api.py`
**Purpose**: Basic API functionality test to ensure endpoints are working before running edge case tests.

**Key Scenarios Tested**:
- Basic CRUD operations (create farmer, farm, trust source)
- Verification session workflow
- Response submission
- Score retrieval
- Error handling

**How to Run**:
```bash
uv run python test_basic_api.py --base-url http://localhost:8000
```

### 1. `test_defaulting_effects_simple.py`
**Purpose**: Test how score changes affect final scores (simplified version without loan endpoints).

**Key Scenarios Tested**:
- Good farmer score decline simulation
- Poor farmer further decline simulation
- Multiple score declines over time
- Score recovery scenarios
- Voucher eligibility based on score thresholds

**How to Run**:
```bash
uv run python test_defaulting_effects_simple.py --base-url http://localhost:8000
```

### 2. `test_defaulting_effects.py`
**Purpose**: Advanced test for farmer default effects (requires loan endpoints).

**Note**: This test may fail if loan endpoints are not implemented. Use the simplified version instead.

**Key Scenarios Tested**:
- Farmer with good score defaults on loan
- Farmer with poor score defaults on loan  
- Multiple defaults over time
- Recovery after default
- Voucher eligibility changes after default

**How to Run**:
```bash
uv run python test_defaulting_effects.py --base-url http://localhost:8000
```

### 2. `test_weight_contribution.py`
**Purpose**: Test how different weights in the scoring system affect final scores.

**Key Scenarios Tested**:
- Individual component contributions (discipline 35%, buyer 30%, etc.)
- Weight sensitivity analysis
- Extreme weight scenarios
- Component failure scenarios
- Weight balance validation

**How to Run**:
```bash
uv run python test_weight_contribution.py --base-url http://localhost:8000
```

### 3. `test_multiple_vouchers.py`
**Purpose**: Test edge cases when more than 3 people from the same category vouch for a farmer.

**Key Scenarios Tested**:
- Exactly 3 people in same category
- More than 3 people in same category (4, 5, 6+)
- Mixed responses in large groups
- All responses agree in large groups
- Extreme disagreement in large groups
- Cross-category vs single-category comparison
- Agreement/disagreement tracking

**How to Run**:
```bash
uv run python test_multiple_vouchers.py --base-url http://localhost:8000
```

### 4. `test_comprehensive_edge_cases.py`
**Purpose**: Comprehensive test suite covering multiple edge cases from scoring.md.

**Key Scenarios Tested**:
- Verifier credibility evolution over time
- Adaptive scoring behavior with new data
- Bias resistance validation
- 4-point forced choice scale validation
- Cross-corroboration effects
- Farm activity integration

**How to Run**:
```bash
uv run python test_comprehensive_edge_cases.py --base-url http://localhost:8000
```

## Prerequisites

1. **Backend Server**: Ensure your Hifadhi backend is running on `http://localhost:8000` (or specify different URL with `--base-url` parameter)

2. **Dependencies**: Install required Python packages:
```bash
pip install httpx
```

3. **Database Setup**: Ensure your test database is properly configured with all schemas

## Test Execution

### Recommended Test Order
1. **Basic API Test** - Ensure endpoints are working
2. **Individual Edge Case Tests** - Test specific scenarios  
3. **Comprehensive Test Suite** - Full system validation

### Running Individual Tests
```bash
# Always start with basic API test
uv run python test_basic_api.py

# Test defaulting effects (simplified version)
uv run python test_defaulting_effects_simple.py

# Test defaulting effects (advanced - may fail if loans not implemented)
uv run python test_defaulting_effects.py

# Test weight contributions  
uv run python test_weight_contribution.py

# Test multiple vouchers
uv run python test_multiple_vouchers.py

# Run comprehensive tests
uv run python test_comprehensive_edge_cases.py
```

### Running with Custom Base URL
```bash
uv run python test_defaulting_effects.py --base-url http://your-server-url:8000
```

### Running All Tests
You can run all tests sequentially:
```bash
echo "Running defaulting effects tests..."
uv run python test_defaulting_effects.py

echo "Running weight contribution tests..."
uv run python test_weight_contribution.py

echo "Running multiple voucher tests..."
uv run python test_multiple_vouchers.py

echo "Running comprehensive edge case tests..."
uv run python test_comprehensive_edge_cases.py
```

## Expected Test Results

### ✅ Passing Tests
- Clear output showing test progression
- Score calculations match expected values
- Edge cases handled appropriately
- No HTTP errors (4xx/5xx status codes)

### ❌ Failing Tests
- HTTP errors indicate server issues
- Score calculations don't match expected values
- Edge cases not handled properly
- Missing expected functionality

## Common Issues and Troubleshooting

### 1. Server Connection Issues
```
FAILED at http://localhost:8000: Connection refused
```
**Solution**: Ensure backend server is running with `uv run uvicorn main:app --reload`

### 2. 422 Validation Errors
```
422 validation error
{"detail":[{"type":"missing","loc":["body","market_actor","reliability_rating"],"msg":"Field required"}]}
```
**Solution**: 
- Run `test_basic_api.py` first to verify basic functionality
- Check API documentation for correct payload structure
- Each participant type requires different fields:
  - `trust_source`: `rating`, `comments`, `personal_knowledge_flag`
  - `market_actor`: `reliability_rating`, `purchase_frequency`, `relationship_months`, `avg_volume_kg`  
  - `social_group`: `consecutive_cycles`, `last_contribution_date`, `contribution_amount`

### 3. Missing Loan Endpoints
```
404 Not Found
{"detail":"Not Found"}
```
**Solution**: 
- Some test scripts assume loan endpoints exist (`/api/farmers/{id}/loans`)
- Current API may not have these endpoints implemented
- Use simplified test versions: `test_defaulting_effects_simple.py` instead of `test_defaulting_effects.py`
- Advanced loan functionality may be implemented in future versions

### 3. Database Schema Issues
```
422 validation error
```
**Solution**: Check database schema matches test expectations

### 4. Missing Endpoints
```
404 not found
```
**Solution**: Verify all API endpoints are implemented

### 5. Test Data Conflicts
Tests may fail if test data conflicts with existing data. Each test creates unique test farmers with UUID-based identifiers.

### 6. Payload Structure Issues
If you get 422 errors for missing fields, ensure you're using the correct payload structure for each participant type. The test scripts have been updated to use the correct structure based on the working `hifadhi_e2e_test.py`.

## Test Data Management

Each test script creates unique test data using UUID identifiers to avoid conflicts:
- Test farmers are named with unique suffixes
- National IDs are prefixed with test categories (DEFAULT-, WEIGHT-, MULTI-, etc.)
- Phone numbers use unique number ranges

## Integration with CI/CD

These tests can be integrated into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Hifadhi Backend Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install httpx
        pip install -r requirements.txt
    - name: Start server
      run: uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
    - name: Run tests
      run: |
        uv run python test_defaulting_effects.py
        uv run python test_weight_contribution.py
        uv run python test_multiple_vouchers.py
        uv run python test_comprehensive_edge_cases.py
```

## Test Coverage

This testing suite covers all major edge cases from scoring.md:

| Edge Case Category | Test Script | Coverage |
|-------------------|-------------|----------|
| Defaulting Effects | `test_defaulting_effects.py` | ✅ Complete |
| Weight Contributions | `test_weight_contribution.py` | ✅ Complete |
| Multiple Vouchers | `test_multiple_vouchers.py` | ✅ Complete |
| Comprehensive Cases | `test_comprehensive_edge_cases.py` | ✅ Complete |

## Contributing

When adding new tests:
1. Follow the existing pattern of creating unique test data
2. Include clear step labels for test progression
3. Provide detailed error messages for debugging
4. Test both positive and negative scenarios
5. Add comments explaining test purpose

## Performance Considerations

- Each test creates new farmer records and verification sessions
- Tests may take 30-60 seconds to complete due to multiple API calls
- Consider running tests during off-peak hours if using shared database
- Test data is automatically cleaned up when tests complete

## Reporting

Test results include:
- Step-by-step progression through test scenarios
- Score comparisons and validation
- Error messages for failures
- Summary of overall test status

For detailed debugging, examine the full output which shows:
- HTTP request/response details
- Score breakdown components
- Individual test case results
- Error traces when applicable