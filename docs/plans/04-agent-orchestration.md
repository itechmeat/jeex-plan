# EPIC 04 — Agent Orchestration & CrewAI Integration

## Mission

Разработать мультиагентную систему на базе CrewAI с четырьмя специализированными агентами, обеспечить их оркестрацию с соблюдением строгих контрактов I/O и интеграцию с векторным поиском для контекстного мышления.

## Why now

Агентная система является ядром продукта JEEX Plan. Без работающих агентов невозможно генерировать документы. CrewAI требует настройки поверх готовой аутентификации и векторного поиска для контекстной работы.

## Success Criteria

- CrewAI 0.186.1+ интегрирован с четырьмя специализированными агентами
- Все агенты используют Pydantic AI контракты для типобезопасности
- Agent orchestrator управляет execution context и correlation IDs
- Агенты имеют доступ к project-specific vector context
- Retry logic и circuit breakers для LLM API взаимодействий
- Agent execution audit trail для troubleshooting

## Stakeholders & Interfaces

- **Primary Owner**: Backend Developer
- **Reviewers**: ML Engineer, Tech Lead
- **External Systems**: LLM API (OpenAI/Claude), CrewAI framework

## Status: COMPLETED ✅

Мультиагентная система на базе CrewAI успешно реализована с полной интеграцией векторного поиска, LLM провайдерами и качественным контролем.

## Tasks

- [x] **04.1.** CrewAI Framework Setup *→ Depends on [Epic 02.4.2](02-authentication.md#024)*
  - [x] **04.1.1.** CrewAI 0.193.2+ installation и configuration
  - [x] **04.1.2.** Base agent class с Pydantic AI contracts
  - [x] **04.1.3.** Agent execution context management
  - [x] **04.1.4.** Correlation ID tracking через agent workflows

- [x] **04.2.** Specialized Agent Implementation *→ Depends on [Epic 03.4.3](03-vector-database.md#034)*
  - [x] **04.2.1.** Business Analyst Agent — project description expert
  - [x] **04.2.2.** Solution Architect Agent — technical architecture specialist
  - [x] **04.2.3.** Project Planner Agent — implementation planning expert
  - [x] **04.2.4.** Engineering Standards Agent — code quality и best practices

- [x] **04.3.** Agent Communication & Memory
  - [x] **04.3.1.** Vector context retrieval integration для agents
  - [x] **04.3.2.** Inter-agent communication protocols
  - [x] **04.3.3.** Agent memory management с project isolation
  - [x] **04.3.4.** Context window optimization для LLM calls

- [x] **04.4.** LLM Integration & Reliability *→ Depends on [Epic 01.5.2](01-infrastructure.md#015)*
  - [x] **04.4.1.** LLM provider abstraction layer
  - [x] **04.4.2.** Tenacity retry logic с exponential backoff
  - [x] **04.4.3.** Circuit breaker implementation для LLM failures
  - [x] **04.4.4.** API key management через Vault integration

- [x] **04.5.** Agent Orchestration Engine
  - [x] **04.5.1.** Workflow coordinator для sequential agent execution
  - [x] **04.5.2.** Progress tracking и status updates
  - [x] **04.5.3.** Error handling и graceful degradation
  - [x] **04.5.4.** Parallel execution support для independent operations

- [x] **04.6.** Validation & Quality Control
  - [x] **04.6.1.** Output validation система для agent results
  - [x] **04.6.2.** Content quality scoring integration
  - [x] **04.6.3.** Agent performance metrics collection
  - [x] **04.6.4.** Automated testing framework для agent behaviors

## Dependencies

**Incoming**:
- [Epic 02.4.2](02-authentication.md#024) — Permission system для agent authorization
- [Epic 03.4.3](03-vector-database.md#034) — Context retrieval для informed agent decisions
- [Epic 01.5.2](01-infrastructure.md#015) — Vault для secure LLM API key storage

**Outgoing**:
- Enables [Epic 05.1.1](05-document-generation.md#051) — Document generation needs working agents
- Enables [Epic 08.2.1](08-quality-assurance.md#082) — QA validation depends on agent outputs
- Enables [Epic 09.2.2](09-observability.md#092) — Agent tracing requires orchestration context

**External**: OpenAI API, Claude API, или alternative LLM providers

## Risks & Mitigations

| Risk | Owner | Impact | Mitigation/Trigger |
|------|-------|--------|-------------------|
| LLM API availability или rate limits | Backend Developer | High | Multiple provider fallback, graceful degradation modes |
| Agent output quality inconsistency | ML Engineer | High | Robust validation rules, output scoring, human feedback loop |
| CrewAI framework bugs или limitations | Backend Developer | Medium | Custom orchestration fallback, active community monitoring |
| Context window limits для complex projects | Backend Developer | Medium | Intelligent context pruning, hierarchical summarization |
| High LLM API costs during development | Backend Developer | Medium | Development mode limits, cost monitoring alerts |

## Acceptance Evidence

- Все четыре агента успешно выполняют base workflows
- Agent orchestration обрабатывает failures без system crashes
- Vector context правильно передается agents для informed decisions
- Pydantic contracts валидируют все agent inputs/outputs без errors
- Circuit breakers активируются при LLM API failures
- Agent execution logs содержат correlation IDs для troubleshooting