---
allowed-tools: Bash(coderabbit:*)
description: Run CodeRabbit analysis and automatically fix all found issues
---

# CodeRabbit Code Review and Auto-Fix

Run CodeRabbit CLI analysis in prompt-only mode optimized for AI agents, then systematically fix all identified issues using the provided instructions.

## Process:

1. **Analysis Phase**: Execute CodeRabbit CLI with `--prompt-only` flag to get AI-optimized output
2. **Fix Phase**: Automatically implement all suggested fixes using the detailed instructions provided by CodeRabbit
3. **Verification**: Ensure all changes maintain code quality and follow project conventions

## Scope:

$ARGUMENTS will be used to specify the scope (default: current directory). Examples:

- `/cr frontend` - analyze only frontend directory as tech-frontend agent
- `/cr frontend/components/ui` - analyze specific frontend module as tech-frontend agent
- `/cr backend` - analyze only backend directory as tech-backend agent
- `/cr backend/app` - analyze specific backend module as tech-backend agent
- `/cr` - analyze entire project (respects .coderabbit.yml filters)

## Instructions:

Run CodeRabbit analysis on ${ARGUMENTS:-.} (current directory if no arguments provided):

!coderabbit --prompt-only ${ARGUMENTS:+--cwd $ARGUMENTS}

Then systematically address each issue found by CodeRabbit:

1. **Read each issue carefully** - understand the problem, location, and suggested fix
2. **Implement the exact fix** suggested in the "Prompt for AI Agent" sections
3. **Maintain code consistency** - follow existing patterns and conventions
4. **Preserve functionality** - ensure fixes don't break existing behavior
5. **Follow project standards** - adhere to patterns defined in CLAUDE.md
6. **Test critical changes** - verify that complex fixes work as expected

## Key Principles:

- **No placeholders or hardcoded values** - implement real, functional code
- **Follow DRY principles** - extract reusable code where suggested
- **Maintain accessibility** - implement keyboard navigation and ARIA labels as recommended
- **Use proper error handling** - replace console.error with standardized error handlers
- **Preserve multi-tenant architecture** - ensure all changes respect tenant isolation
- **Follow security best practices** - implement proper validation and sanitization

## Agents:

When analyzing specific parts of the project, the appropriate specialized agents will be used automatically based on the command arguments:

- If the command contains `frontend` argument (e.g., `/cr frontend`), the tech-frontend agent should be used
- If the command contains `backend` argument (e.g., `/cr backend`), the tech-backend agent should be used
- For mixed or general analysis, both agents may be consulted as needed

## Expected Output:

- List of all issues found and their status (fixed/skipped/needs-review)
- Summary of changes made
- Any issues that require manual review or additional context
- Verification that all critical functionality remains intact

Execute this command step by step, providing clear feedback on progress and any decisions made during the fixing process.
