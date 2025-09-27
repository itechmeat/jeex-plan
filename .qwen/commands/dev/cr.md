---
allowed-tools: Bash(coderabbit:*), Task
description: Run CodeRabbit analysis and automatically fix all found issues with smart agent selection
argument-hint: [scope] [additional-instructions] (frontend/backend/all) (optional custom prompt)
---

# CodeRabbit Code Review and Auto-Fix

Run CodeRabbit CLI analysis in prompt-only mode optimized for AI agents, then systematically fix all identified issues using appropriate specialized agents.

## Agent Selection Logic:

**Step 1: Argument Analysis and Agent Selection**

- Argument `frontend` or path contains `frontend/` → activate the `tech-frontend` agent
- Argument `backend` or path contains `backend/` → activate the `tech-python` agent
- Argument `all` or no argument provided → analyze the entire project and auto-select agents based on results

## Process:

1. **Analysis Phase**: Execute CodeRabbit CLI with `--prompt-only` flag to get AI-optimized output
2. **Agent Activation**: Based on scope argument, activate appropriate specialized agent using Task tool
3. **Fix Phase**: Let the specialized agent implement all suggested fixes
4. **Verification**: Ensure all changes maintain code quality and follow project conventions

## Scope Examples:

- `/dev:cr frontend` - analyze frontend directory with tech-frontend agent
- `/dev:cr backend` - analyze backend directory with tech-python agent
- `/dev:cr frontend/components/ui` - analyze specific frontend module with tech-frontend agent
- `/dev:cr backend/app` - analyze specific backend module with tech-python agent
- `/dev:cr all` - analyze entire project with appropriate agents
- `/dev:cr` - same as 'all' - analyze entire project

## Instructions:

**Step 1: CodeRabbit Analysis**
Run CodeRabbit analysis on ${ARGUMENTS:-.} (current directory if no arguments provided):

!timeout 900 coderabbit --prompt-only ${ARGUMENTS:+--cwd $ARGUMENTS}

**IMPORTANT: Analysis Duration**
CodeRabbit analysis can take up to 10 minutes to complete, especially for large changesets or projects with many files. **Wait patiently** - do NOT interrupt the process.

**CRITICAL: Error Handling**
If CodeRabbit returns any error (rate limits, authentication, network issues, etc.):

1. **Immediately stop execution** - do NOT proceed with agent activation
2. **Notify the user** about the specific error encountered
3. **Provide guidance** on how to resolve the issue (e.g., wait for rate limit reset, check authentication)
4. **Exit gracefully** without launching any agents

Common error scenarios:

- **Rate limit exceeded**: "CodeRabbit API rate limit exceeded. Please wait and try again later."
- **Authentication failed**: "CodeRabbit authentication failed. Please check your API credentials."
- **Network/connectivity issues**: "CodeRabbit API is unreachable. Please check your internet connection."
- **Invalid arguments**: "Invalid CodeRabbit arguments provided. Please check the command syntax."

**Step 2: Agent Selection and Activation**
**ONLY proceed if CodeRabbit analysis completed successfully without errors.**

**If the argument equals "frontend" or includes "frontend/":**

```
Use the Task tool with parameters:
- subagent_type: "tech-frontend"
- description: "Fix CodeRabbit frontend issues"
- prompt: "Perform a systematic fix for every issue CodeRabbit found in the frontend code: [insert the CodeRabbit analysis output]. Resolve each issue according to the guidance in the 'Prompt for AI Agent' sections. Follow all React 19+, TypeScript, accessibility, and performance principles."
```

**If the argument equals "backend" or includes "backend/":**

```
Use the Task tool with parameters:
- subagent_type: "tech-python"
- description: "Fix CodeRabbit backend issues"
- prompt: "Perform a systematic fix for every issue CodeRabbit found in the backend code: [insert the CodeRabbit analysis output]. Resolve each issue according to the guidance in the 'Prompt for AI Agent' sections. Follow architectural principles, security requirements, and multi-tenant isolation."
```

**If the argument equals "all" or is omitted:**

```
1. Review the CodeRabbit output and identify the types of files with issues
2. If there are frontend issues, launch the tech-frontend agent
3. If there are backend issues, launch the tech-python agent
4. When required, run both agents in parallel
```

**Step 3: Specialized Agent Execution**

The activated agent must:

1. **Read each issue carefully** - understand the problem, location, and proposed fix
2. **Implement exact fixes** - apply the precise corrections from the "Prompt for AI Agent" sections
3. **Maintain consistency** - follow existing patterns and conventions
4. **Preserve functionality** - ensure the fixes do not break functionality
5. **Follow project standards** - comply with the principles in CLAUDE.md
6. **Test critical changes** - validate the complex fixes

## Key Principles for Agents:

- **No placeholders or hardcoded values** - implement real, functional code
- **Follow DRY principles** - extract reusable code where suggested
- **Maintain accessibility** - implement keyboard navigation and ARIA labels as recommended
- **Use proper error handling** - replace console.error with standardized error handlers
- **Preserve multi-tenant architecture** - ensure all changes respect tenant isolation
- **Follow security best practices** - implement proper validation and sanitization

## Critical Requirements:

- **Always provide the exact `subagent_type`** in the Task tool
- **Confirm the agent activation** - the agent must introduce itself when it starts
- **Pass the full CodeRabbit output** into the agent prompt
- **Retry with corrected parameters** if agent activation fails

## Expected Output from Specialized Agents:

- **Analysis Summary**: List of all issues found and their categorization
- **Fix Status**: Status of each issue (fixed/skipped/needs-review)
- **Changes Summary**: Detailed summary of changes made by the agent
- **Manual Review Items**: Any issues requiring manual review or additional context
- **Quality Verification**: Confirmation that critical functionality remains intact
- **Test Results**: Results of type-check, lint, or other verification commands

## Command Execution Flow:

1. **Run the CodeRabbit analysis** with the provided scope
2. **Determine the analysis type** based on the argument
3. **Activate the matching agent** through the Task tool with the exact subagent_type
4. **Pass the CodeRabbit output** to the agent for fixes
5. **Collect the agent report** detailing the applied changes
6. **Verify quality** - run linters/type-checks when necessary

## Usage Examples:

- `/dev:cr frontend` - full analysis and remediation of the frontend code by the tech-frontend agent
- `/dev:cr backend` - full analysis and remediation of the backend code by the tech-python agent
- `/dev:cr frontend/src/components` - focused analysis of specific frontend components
- `/dev:cr backend/app/services` - focused analysis of specific backend services
- `/dev:cr` - full project analysis with automatic agent selection

**Important:** Always verify that the agent actually activated—the agent must introduce itself at the start of its response!
