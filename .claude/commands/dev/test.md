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

!timeout 900 cd tests && pnpm run test || true

**Step 2: Run Backend Tests**
Execute backend test suite:

!timeout 600 cd backend && docker-compose exec api pytest -v

**Step 3: Analyze Test Results**
Carefully review the test output to identify:

1. **Failed tests and their locations**
2. **Error types and root causes**
3. **Affected components and services**

**Step 4: Agent Selection and Activation**
Based on test results, activate appropriate agents:

**For frontend/E2E issues:**

```
Use the Task tool with parameters:
- subagent_type: "tech-frontend"
- description: "Fix E2E test failures"
- prompt: "Fix the following E2E test failures: [insert E2E test errors]. Resolve UI component issues, form validation problems, navigation errors, or state management issues. Follow React 19+, TypeScript strict mode, and accessibility standards. Ensure all fixes maintain multi-tenant architecture and security requirements."
```

**For backend test failures:**

```
Use the Task tool with parameters:
- subagent_type: "tech-python"
- description: "Fix backend test failures"
- prompt: "Fix the following backend test failures: [insert backend test errors]. Resolve API endpoint issues, business logic errors, database problems, authentication failures, or tenant isolation violations. Follow FastAPI best practices, async patterns, security requirements, and multi-tenant architecture principles."
```

**For test infrastructure issues:**

```
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