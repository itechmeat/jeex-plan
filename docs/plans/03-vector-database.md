# EPIC 03 — Vector Database & Embedding Service

## Mission

Создать систему векторного поиска на базе Qdrant с мультитенантной архитектурой, реализовать embedding service для обработки текста и обеспечить эффективный семантический поиск по контексту проектов.

## Why now

Векторный поиск является ключевым компонентом для агентной системы, которая должна находить релевантный контекст проекта для генерации качественных документов. Мультитенантная изоляция критична для безопасности.

## Success Criteria

- Qdrant 1.15.4+ развернут с оптимизированной конфигурацией для мультитенантности
- Embedding service обрабатывает текст с нормализацией и chunking
- Strict tenant/project isolation для всех vector operations
- HNSW индекс настроен для payload-filtering efficiency
- Semantic search API с sub-200ms latency для project context

## Stakeholders & Interfaces

- **Primary Owner**: Backend Developer
- **Reviewers**: ML Engineer, Tech Lead
- **External Systems**: Qdrant, OpenAI Embedding API (или альтернатива)

## Tasks

- [ ] **03.1.** Qdrant Infrastructure Setup *→ Depends on [Epic 01.1.1](01-infrastructure.md#011)*
  - [ ] **03.1.1.** Qdrant 1.15.4+ deployment с Docker configuration
  - [ ] **03.1.2.** Multi-tenant collection schema design
  - [ ] **03.1.3.** HNSW parameters optimization для payload filtering
  - [ ] **03.1.4.** Volume configuration для persistent vector storage

- [ ] **03.2.** Multi-tenant Vector Architecture
  - [ ] **03.2.1.** Payload schema design (tenant_id, project_id, type, version)
  - [ ] **03.2.2.** Collection initialization с proper indexing
  - [ ] **03.2.3.** Server-side filtering middleware *→ Depends on [Epic 02.3.3](02-authentication.md#023)*
  - [ ] **03.2.4.** Tenant isolation validation tests

- [ ] **03.3.** Embedding Service Development
  - [ ] **03.3.1.** Text preprocessing pipeline (normalization, chunking)
  - [ ] **03.3.2.** Embedding model integration (единая модель для MVP)
  - [ ] **03.3.3.** Batch processing для efficient API usage
  - [ ] **03.3.4.** Error handling и retry logic для external API calls

- [ ] **03.4.** Vector Operations API
  - [ ] **03.4.1.** Document storage API с automatic embedding
  - [ ] **03.4.2.** Semantic search endpoint с filtering
  - [ ] **03.4.3.** Context retrieval для agent operations
  - [ ] **03.4.4.** Vector management (update, delete) operations

- [ ] **03.5.** Performance Optimization *→ Depends on [Epic 01.4.3](01-infrastructure.md#014)*
  - [ ] **03.5.1.** Redis caching для frequent searches
  - [ ] **03.5.2.** Connection pooling для Qdrant client
  - [ ] **03.5.3.** Embedding deduplication logic
  - [ ] **03.5.4.** Search result caching strategies

- [ ] **03.6.** Quality Assurance
  - [ ] **03.6.1.** Search relevance testing framework
  - [ ] **03.6.2.** Multi-tenant isolation verification
  - [ ] **03.6.3.** Performance benchmarking scripts
  - [ ] **03.6.4.** Index health monitoring endpoints

## Dependencies

**Incoming**:
- [Epic 01.1.1](01-infrastructure.md#011) — Docker infrastructure для Qdrant deployment
- [Epic 01.4.3](01-infrastructure.md#014) — Redis для caching search results
- [Epic 02.3.3](02-authentication.md#023) — Tenant isolation middleware

**Outgoing**:
- Enables [Epic 04.2.1](04-agent-orchestration.md#042) — Agents need context retrieval
- Enables [Epic 05.2.2](05-document-generation.md#052) — Document generation needs previous context
- Enables [Epic 08.1.1](08-quality-assurance.md#081) — QA needs semantic consistency checks

**External**: Embedding API provider (OpenAI, HuggingFace, или локальная модель)

## Risks & Mitigations

| Risk | Owner | Impact | Mitigation/Trigger |
|------|-------|--------|-------------------|
| Qdrant multi-tenant performance degradation | Backend Developer | High | Monitor payload filtering performance, consider sharding |
| Embedding API rate limits или costs | Backend Developer | Medium | Local model fallback, adaptive batching strategies |
| HNSW configuration не оптимальна для use case | ML Engineer | Medium | A/B testing configurations, benchmark different settings |
| Cross-tenant data leakage в vector space | Backend Developer | Critical | Automated isolation testing, payload validation |
| Embedding model quality insufficient для domain | ML Engineer | Medium | Domain-specific model fine-tuning или model switching |

## Acceptance Evidence

- Multi-tenant collection создана с proper payload schema
- Search queries возвращают только tenant/project-specific results
- Embedding pipeline обрабатывает документы без errors
- Search latency < 200ms для typical project context queries
- Automated tests подтверждают tenant isolation
- Vector index health checks проходят successfully