---
allowed-tools: Bash(make:*), Bash(docker-compose:*), Bash(pnpm:*), Task
description: Run comprehensive testing - E2E tests and backend tests with automatic issue fixing
argument-hint: [clarifying-prompt] (optional custom prompt for agents)
---

# Comprehensive Testing Command

Run complete testing suite including E2E tests (Playwright) and backend tests (pytest), then automatically fix any identified issues using appropriate specialized agents.

## Agent Selection Logic

**Step 1: Test Analysis and Agent Selection**

- If E2E tests fail → activate appropriate agents based on failure type
- If backend tests fail → activate appropriate agents based on failure type
- If both fail → activate multiple agents in parallel

## Process

1. **E2E Testing Phase**: Execute Playwright tests in `tests/e2e/` directory
2. **Backend Testing Phase**: Execute pytest tests in `backend/tests/` directory
3. **Agent Activation**: Based on test results, activate appropriate specialized agents
4. **Fix Phase**: Let specialized agents implement fixes for identified issues
5. **Verification**: Ensure all changes maintain code quality and functionality

## Agent Selection by Issue Type

**E2E Test Failures:**

- Frontend component issues → activate `tech-frontend` agent
- API endpoint issues → activate `tech-python` agent
- Integration/flow issues → activate `tech-qa` agent

**Backend Test Failures:**

- API/business logic errors → activate `tech-python` agent
- Database/model issues → activate `tech-python` agent
- Authentication/security issues → activate `tech-python` agent
- Tenant isolation issues → activate `tech-python` agent
- Performance issues → activate `tech-qa` agent

**Test Infrastructure Issues:**

- Flaky tests → activate `tech-qa` agent
- Coverage gaps → activate `tech-qa` agent
- Test data/setup issues → activate `tech-qa` agent

## Instructions

**Step 1: Run E2E Tests**
Execute Playwright test suite:

!bash -c 'echo "=== E2E TESTS STARTING ===" && cd tests && timeout 900 pnpm run test; STATUS=$?; echo ""; echo "=== E2E TESTS COMPLETED ==="; echo "__PW_STATUS:$STATUS"; echo "=== END E2E TESTS ===" ; exit $STATUS' || echo "\_\_PW_FAILED"

**Step 2: Run Backend Tests**
Execute backend test suite:

!bash -c 'echo "=== BACKEND TESTS STARTING ===" && cd backend && timeout 900 docker compose run --rm -T api pytest -q --tb=short; STATUS=$?; echo ""; echo "=== BACKEND TESTS COMPLETED ==="; echo "__PY_STATUS:$STATUS"; echo "=== END BACKEND TESTS ==="; exit $STATUS' || echo "\_\_PY_FAILED"

**Step 3: Analyze Test Results**
Carefully review the test output to identify:

1. **Failed tests and their locations**
2. **Error types and root causes**
3. **Affected components and services**

**Step 3.5: Parse Status Codes and Determine Agent Activation**

Extract and interpret test status codes from command output:

**Status Code Extraction:**

- Look for `=== E2E TESTS COMPLETED ===` followed by `__PW_STATUS:<code>` in E2E test output
- Look for `=== BACKEND TESTS COMPLETED ===` followed by `__PY_STATUS:<code>` in backend test output
- Look for `__PW_FAILED` or `__PY_FAILED` markers if tests were terminated/failed
- Status code `0` = tests passed (no agent activation needed)
- Status code `1` = tests failed (requires agent activation)
- Status code `>1` = command/infrastructure error (activate tech-qa agent)
- Presence of `__FAILED` marker = critical failure (activate tech-qa agent)

**Pattern Matching for Agent Selection:**

Use regex patterns to identify failure types and select appropriate agents:

**E2E Test Failure Patterns (`__PW_STATUS:1`):**

```text
Frontend Component Issues → tech-frontend:
- Error: Component .* (failed to render|not found)
- TypeError.*\.tsx
- React.*Hook.*error
- State.*undefined
- props\..*is not a function

API Endpoint Issues → tech-python:
- Error:.*(/api/v1/|fetch.*failed)
- Status.*[45]\d{2}
- Network.*error.*localhost:\d+/api
- POST|GET|PUT|DELETE.*failed

Integration/Flow Issues → tech-qa:
- Timeout.*waiting for
- expect\(.*\)\.toBe.*failed
- Screenshot.*mismatch
- Navigation.*failed
```

**Backend Test Failure Patterns (`__PY_STATUS:1`):**

```text
API/Business Logic → tech-python:
- AssertionError.*test_.*api
- /api/v1/.*returned.*[45]\d{2}
- ValidationError
- Pydantic.*validation error

Database/Model Issues → tech-python:
- sqlalchemy\..*Error
- IntegrityError
- UNIQUE constraint failed
- ForeignKeyViolation

Authentication/Security → tech-python:
- (tenant_id|authentication|authorization).*error
- JWT.*invalid
- Unauthorized|Forbidden
- RBAC.*denied

Tenant Isolation → tech-python:
- test_.*tenant.*failed
- Cross-tenant.*leak
- isolation.*violated

Performance Issues → tech-qa:
- test_.*performance.*failed
- Timeout after \d+ seconds
- Memory.*exceeded
```

**Automated Agent Selection Algorithm:**

```python
# Pseudo-code for agent selection
def select_agents(pw_status, py_status, test_output):
    agents_to_activate = []

    # Parse E2E test failures
    if pw_status == 1:
        if re.search(r'(Component .* failed|React.*error|props\..*function)', test_output):
            agents_to_activate.append('tech-frontend')
        if re.search(r'(/api/v1/|Status.*[45]\d{2}|fetch.*failed)', test_output):
            agents_to_activate.append('tech-python')
        if re.search(r'(Timeout.*waiting|expect.*toBe.*failed)', test_output):
            agents_to_activate.append('tech-qa')

    # Parse backend test failures
    if py_status == 1:
        if re.search(r'(AssertionError|ValidationError|api.*[45]\d{2})', test_output):
            agents_to_activate.append('tech-python')
        if re.search(r'(tenant_id|authentication|authorization|JWT)', test_output):
            agents_to_activate.append('tech-python')
        if re.search(r'(performance.*failed|Timeout after|Memory.*exceeded)', test_output):
            agents_to_activate.append('tech-qa')

    # Infrastructure errors
    if pw_status > 1 or py_status > 1:
        agents_to_activate.append('tech-qa')

    return list(set(agents_to_activate))  # Remove duplicates
```

**Decision Matrix:**

| Status Codes/Markers | Error Pattern                | Agent(s) to Activate        |
| -------------------- | ---------------------------- | --------------------------- |
| `__PW_STATUS:1`      | Component/React errors       | `tech-frontend`             |
| `__PW_STATUS:1`      | API endpoint errors          | `tech-python`               |
| `__PW_STATUS:1`      | Timeout/assertion errors     | `tech-qa`                   |
| `__PY_STATUS:1`      | API/validation errors        | `tech-python`               |
| `__PY_STATUS:1`      | Authentication/tenant errors | `tech-python`               |
| `__PY_STATUS:1`      | Performance/timeout errors   | `tech-qa`                   |
| Both `1`             | Multiple patterns            | Multiple agents in parallel |
| Any `>1`             | Infrastructure failure       | `tech-qa`                   |
| `__PW_FAILED`        | E2E test crash/timeout       | `tech-qa`                   |
| `__PY_FAILED`        | Backend test crash/timeout   | `tech-qa`                   |

**Example Output Parsing:**

```bash
# Output contains:
# ... test output ...
# === E2E TESTS COMPLETED ===
# __PW_STATUS:1
# === END E2E TESTS ===
# === BACKEND TESTS COMPLETED ===
# __PY_STATUS:0
# === END BACKEND TESTS ===

# Parse: E2E failed (status 1), Backend passed (status 0)
# Scan E2E output (between START and END markers) for patterns:
# Found: "Error: Component LoginForm failed to render"
# Decision: Activate tech-frontend agent
```

**Step 4: Agent Selection and Activation**
Based on test results, activate appropriate agents:

**For frontend/E2E issues:**

```text
Use the Task tool with parameters:
- subagent_type: "tech-frontend"
- description: "Fix E2E test failures"
- prompt: "Fix the following E2E test failures: [insert E2E test errors]. Resolve UI component issues, form validation problems, navigation errors, or state management issues. Follow React 19+, TypeScript strict mode, and accessibility standards. Ensure all fixes maintain multi-tenant architecture and security requirements."
```

**For backend test failures:**

```text
Use the Task tool with parameters:
- subagent_type: "tech-python"
- description: "Fix backend test failures"
- prompt: "Fix the following backend test failures: [insert backend test errors]. Resolve API endpoint issues, business logic errors, database problems, authentication failures, or tenant isolation violations. Follow FastAPI best practices, async patterns, security requirements, and multi-tenant architecture principles."
```

**For test infrastructure issues:**

```text
Use the Task tool with parameters:
- subagent_type: "tech-qa"
- description: "Fix test infrastructure issues"
- prompt: "Fix the following test infrastructure issues: [insert test errors]. Resolve flaky test problems, coverage gaps, test data issues, or configuration problems. Follow testing best practices and maintain test quality standards using Playwright, pytest, and appropriate mocking strategies."
```

**For multiple issue types:**
Launch agents in parallel for each issue type identified.

**Step 5: Specialized Agent Execution**

The activated agent must:

1. **Analyze each failure** - understand the root cause and error context
2. **Implement targeted fixes** - address the specific test failures
3. **Maintain test coverage** - ensure fixes don't break existing tests
4. **Follow project standards** - comply with CLAUDE.md requirements
5. **Verify fixes** - re-run affected tests to confirm resolution

## Key Principles for Agents

- **Fix root causes** - don't just suppress symptoms
- **Maintain test coverage** - ensure comprehensive testing after fixes
- **Follow multi-tenant architecture** - ensure all changes respect tenant isolation
- **Use appropriate tools** - leverage configured testing frameworks and utilities
- **Document fixes** - provide clear explanations of changes made

## Critical Requirements

- **Always provide the exact `subagent_type`** in the Task tool
- **Confirm agent activation** - the agent must introduce itself when it starts
- **Pass specific test failure details** - include exact error messages and stack traces
- **Retry with corrected parameters** if agent activation fails

## Expected Output from Specialized Agents

- **Failure Analysis**: Summary of test failures and their root causes
- **Fix Status**: Status of each failure (fixed/skipped/needs-review)
- **Changes Summary**: Detailed list of files modified and fixes applied
- **Test Results**: Output from re-running affected tests
- **Quality Confirmation**: Assurance that fixes don't introduce new issues

## Command Execution Flow

1. **Run E2E tests** using Playwright
2. **Run backend tests** using pytest
3. **Analyze failures** to identify issue types and affected areas
4. **Activate matching agents** based on failure categorization
5. **Pass specific failure details** to each agent
6. **Collect agent reports** detailing applied changes
7. **Verify fixes** - re-run tests to confirm resolution

## Usage Examples

- `/dev:test` - run comprehensive testing and fix all found issues
- `/dev:test "focus on authentication tests"` - run tests with specific focus
- `/dev:test "prioritize tenant isolation tests"` - run tests with security emphasis

**Important:** Always verify that agents actually activated - each agent must introduce itself at the start of its response!
