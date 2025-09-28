# JEEX Plan Technical Specification

This document contains detailed technical requirements, API specifications, database schemas, and configurations for implementing JEEX Plan. All components are designed with multi-tenant architecture, scalability, and security in mind.

## 1) Технический стек

Выбор технологий продиктован необходимостью создания надежной, масштабируемой системы с поддержкой мультиагентной архитектуры и векторного поиска. Все компоненты интегрируются через четко определенные API и обеспечивают горизонтальное масштабирование.

### 1.1 Backend

Серверная часть построена на современном Python-стеке с акцентом на производительность и типобезопасность:

- **API Framework:** FastAPI 0.116.2+ (Python) — высокопроизводительный веб-фреймворк с автоматической генерацией OpenAPI документации, встроенной валидацией и Swagger UI для интерактивного тестирования API
- **Agent Framework:** CrewAI 0.186.1+ для мультиагентной архитектуры — orchestration специализированных агентов с поддержкой различных LLM
- **Структурирование I/O:** Pydantic AI 1.0.8+ для контрактов между агентами — строгая типизация и валидация данных на всех уровнях
- **Primary Database:** PostgreSQL 18+ — надежное хранение документов, версий и метаданных с ACID-гарантиями
- **Database Migrations:** Alembic для schema versioning и безопасных миграций БД с automatic downgrade support
- **Vector Database:** Qdrant 1.15.4+ для эмбеддингов и контекста — специализированная БД для семантического поиска с мультитенантностью
- **Cache/Queue:** Redis 8.2+ для буферизации и квот — быстрое кэширование и управление очередями задач
- **Authentication:** OAuth2 — стандартная аутентификация с поддержкой различных провайдеров
- **Streaming:** Server-Sent Events (SSE) — real-time обновления прогресса генерации документов
- **Reliability:** Tenacity для retry logic и circuit breakers при взаимодействии с внешними LLM API
- **Observability:** OpenTelemetry для distributed tracing с автоматической инструментацией FastAPI
- **Content Quality:** textstat для readability scoring документов и language-check для grammar validation
- **Document Processing:** python-markdown с extensions (Mermaid, tables, TOC) для enhanced Markdown rendering

### 1.2 Frontend

Клиентская часть создана как современное SPA-приложение с акцентом на UX и производительность:

- **Framework:** React.js + Vite — быстрая разработка и hot reload, оптимизированная сборка для production
- **Language:** TypeScript — статическая типизация для безопасности и maintainability кода
- **UI Components:** RadixUI — доступные, композитные компоненты с полной кастомизацией стилей
- **Styling:** CSS Modules с CSS Nesting — изолированные стили с поддержкой переменных и вложенных селекторов
- **Development Port:** 5200 — настроенный через Vite configuration для локальной разработки
- **Deployment:** Выполняется локально вне Docker окружения для удобства разработки и hot reload

### 1.3 Infrastructure

Инфраструктура спроектирована для простого развертывания и горизонтального масштабирования:

- **Containerization:** Docker — единообразное развертывание во всех окружениях с изоляцией зависимостей
- **Reverse Proxy:** Nginx — TLS-терминация, компрессия, load balancing и passthrough для SSE
- **Observability:** OpenTelemetry stack — распределенная трассировка, метрики и логи для мониторинга производительности

#### Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| Frontend (local) | 5200 | React + Vite development server |
| API | 5210 | FastAPI backend |
| PostgreSQL | 5220 | Primary database |
| Qdrant | 5230 | Vector database |
| Redis | 5240 | Cache and queues |
| Nginx | 80, 443 | Reverse proxy and TLS |
| OpenTelemetry | 4317, 4318, 8888 | Telemetry (gRPC, HTTP, metrics) |
| HashiCorp Vault | 5250 | Secrets management |

#### Deployment Features

- **Frontend:** Runs locally via `pnpm run dev` for development convenience
- **Backend:** Containerized via docker-compose for isolation and reproducibility
- **Nginx:** Proxies frontend through `host.docker.internal:5200`

### 1.4 Embedding Service

Специализированный сервис для работы с векторными представлениями текста:

- **Text Processing:** Нормализация текста, интеллектуальный чанкинг и дедупликация контента
- **Model:** Единая модель эмбеддингов для MVP — обеспечивает консистентность поиска и эффективную мультитенантность
- **Vector Computation:** Параллельное вычисление и индексация векторов с поддержкой батчинга

### 1.5 Минимальные версии компонентов

Для обеспечения совместимости и доступа к последним возможностям требуются следующие минимальные версии:

| Component   | Minimum Version | Justification                                                 |
| ----------- | ---------------- | ------------------------------------------------------------ |
| FastAPI     | 0.116.2+         | Improved dependency injection, better async support         |
| CrewAI      | 0.186.1+         | Enhanced multi-agent orchestration, memory management       |
| Pydantic AI | 1.0.8+           | Stable API, advanced validation features                    |
| PostgreSQL  | 18+              | Enhanced JSON/JSONB support, improved performance           |
| Qdrant      | 1.15.4+          | Multi-tenancy optimizations, payload filtering improvements |
| Redis       | 8.2+             | Improved memory efficiency, enhanced pub/sub                |
| Tenacity    | 9.0+             | Robust retry mechanisms, circuit breaker patterns          |
| OpenTelemetry | 1.27+          | FastAPI auto-instrumentation, distributed tracing          |
| textstat    | 0.7.0+           | Document readability scoring (Flesch-Kincaid, etc.)        |
| python-markdown | 3.7+          | Enhanced Markdown processing with Mermaid and table support |
| Alembic     | 1.13+            | Database schema migrations with automatic downgrade support |

```mermaid
graph TB
    subgraph "Client Layer"
        BROWSER[Web Browser<br/>React + TypeScript]
    end

    subgraph "Infrastructure Layer"
        NGINX[Nginx Reverse Proxy<br/>TLS + Load Balancing]
        DOCKER[Docker Containers<br/>Orchestration]
    end

    subgraph "Application Layer"
        FASTAPI[FastAPI Backend<br/>Python + Pydantic]
        CREW[CrewAI Orchestrator<br/>Multi-Agent System]
        EMBED[Embedding Service<br/>Vector Processing]
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Documents & Metadata)]
        QDRANT[(Qdrant<br/>Vector Database)]
        REDIS[(Redis<br/>Cache & Queues)]
    end

    subgraph "External Services"
        LLM[LLM Providers<br/>OpenAI, Claude, etc.]
        OAUTH[OAuth2 Providers<br/>Google, GitHub, etc.]
    end

    subgraph "Observability"
        OTEL[OpenTelemetry<br/>Traces & Metrics]
    end

    BROWSER --> NGINX
    NGINX --> FASTAPI
    FASTAPI --> CREW
    FASTAPI --> EMBED
    FASTAPI --> POSTGRES
    FASTAPI --> REDIS
    EMBED --> QDRANT
    CREW --> LLM
    FASTAPI --> OAUTH

    FASTAPI --> OTEL
    CREW --> OTEL
    EMBED --> OTEL

    DOCKER -.-> FASTAPI
    DOCKER -.-> EMBED
    DOCKER -.-> POSTGRES
    DOCKER -.-> QDRANT
    DOCKER -.-> REDIS
```

## 2) Мультитенантная архитектура Qdrant

Qdrant настроена для эффективной мультитенантности с логической изоляцией данных через payload-фильтрацию. Этот подход обеспечивает баланс между производительностью и изоляцией, позволяя масштабироваться до тысяч тенантов в единой инфраструктуре.

### 2.1 Базовая конфигурация

Используется единая коллекция с payload-фильтрацией для логического разделения тенантов. Данный подход оптимален для MVP, где количество тенантов не превышает тысячи, а требования к физической изоляции данных отсутствуют.

**Payload структура для каждого вектора:**

Каждый вектор в Qdrant содержит структурированные метаданные, обеспечивающие точную фильтрацию и категоризацию контента:

```json
{
  "tenant_id": "string", // Идентификатор арендатора
  "project_id": "string", // Идентификатор проекта внутри тенанта
  "type": "knowledge | memory", // Тип данных: фактические знания или контекстная память
  "visibility": "private | public", // Уровень доступа к документу
  "version": "string", // Версия документа для отслеживания изменений
  "lang": "string", // Язык контента (ISO 639-1)
  "tags": ["array", "of", "strings"] // Произвольные теги для дополнительной категоризации
}
```

### 2.2 Конфигурация HNSW для мультитенантности

Специальная настройка алгоритма HNSW оптимизирует производительность для сценариев с частой payload-фильтрацией:

```json
{
  "hnsw_config": {
    "m": 0, // Отключаем глобальный граф
    "payload_m": 16 // Создаем payload-специфичные связи
  }
}
```

**Обоснование конфигурации:**

- `payload_m: 16` — создает дополнительные связи между векторами с похожими payload, ускоряя фильтрованный поиск
- `m: 0` — отключает глобальный индекс, фокусируясь на tenant-specific поиске и экономя память

### 2.3 Индексирование и фильтрация

Система индексирования обеспечивает быструю изоляцию данных и предотвращает cross-tenant утечки:

- **Обязательный payload-индекс:** автоматическое создание индекса по `tenant_id` для мгновенной фильтрации
- **Строгие фильтры:** каждый запрос принудительно включает фильтр `(tenant_id AND project_id)` на уровне сервера
- **Серверная защита:** клиентские приложения не имеют возможности обойти tenant/project фильтры

### 2.4 Оптимизации производительности

Современные версии Qdrant включают специальные оптимизации для мультитенантных сценариев:

- **Qdrant 1.11+:** интеллектуальное размещение векторов одного тенанта в соседних блоках на диске
- **Пакетное чтение:** минимизация I/O операций при обработке tenant-specific запросов
- **Adaptive квоты:** динамические ограничения на количество точек в индексе и частоту запросов по тенантам

## 3) API Спецификация

RESTful API построено на принципах resource-oriented design с поддержкой real-time обновлений через Server-Sent Events. Все endpoints включают автоматическую tenant/project изоляцию на уровне middleware.

### 3.1 Authentication Endpoints

Аутентификация реализована через OAuth2 с поддержкой множественных провайдеров:

```http
POST /auth/login       # Инициация OAuth2 flow
POST /auth/logout      # Завершение сессии и очистка токенов
GET  /auth/me          # Получение профиля текущего пользователя
```

### 3.2 Project Management

CRUD операции для управления проектами с автоматической tenant-изоляцией:

```http
GET    /projects                    # Список проектов текущего пользователя
POST   /projects                    # Создание нового проекта
       # Body: {name: string, language?: string}
GET    /projects/{id}               # Детали конкретного проекта
PUT    /projects/{id}               # Обновление проекта
       # Body: {name?: string, language?: string}
DELETE /projects/{id}               # Удаление проекта (soft delete)
```

### 3.3 Document Generation Workflow

Четырехэтапный процесс генерации документации с участием специализированных агентов:

```http
POST /projects/{id}/step1          # Business Analyst - About Document
POST /projects/{id}/step2          # Engineering Standards - Specs Document
POST /projects/{id}/step3          # Solution Architect - Architecture Document
POST /projects/{id}/step4          # Project Planner - Implementation Plans (overview + epics)
```

Каждый endpoint поддерживает итеративные уточнения и валидацию результатов.

### 3.4 Progress and Streaming

Real-time мониторинг прогресса генерации с поддержкой reconnection:

```http
GET /projects/{id}/progress        # Текущий статус и прогресс всех этапов
GET /projects/{id}/events          # SSE stream для real-time обновлений
```

### 3.5 Export

Генерация и загрузка финального пакета документов:

```http
POST /projects/{id}/export         # Создание ZIP-архива с документами
GET  /exports/{export_id}          # Скачивание готового архива
```

### 3.6 API Flow Diagram

Диаграмма показывает типичный flow пользователя через все этапы создания документации:

```mermaid
sequenceDiagram
    participant Client as Web Client
    participant API as FastAPI Gateway
    participant Auth as OAuth2 Service
    participant Agent as Agent Orchestrator
    participant DB as PostgreSQL
    participant VDB as Qdrant

    Client->>API: POST /auth/login
    API->>Auth: OAuth2 Flow
    Auth-->>Client: Access Token

    Client->>API: POST /projects {name, language}
    API->>DB: Create Project Record
    DB-->>API: Project ID
    API-->>Client: Project Created

    Client->>API: POST /projects/{id}/step1
    API->>Agent: Invoke Business Analyst
    Agent->>DB: Save About v1
    Agent->>VDB: Store Knowledge Embeddings
    API-->>Client: SSE Progress Updates
    API-->>Client: About Document Ready

    Client->>API: POST /projects/{id}/step2
    API->>Agent: Invoke Engineering Standards
    Agent->>VDB: Query Project Context
    Agent->>DB: Save Specs v1
    API-->>Client: SSE Progress Updates
    API-->>Client: Specs Document Ready

    Client->>API: POST /projects/{id}/step3
    API->>Agent: Invoke Solution Architect
    Agent->>VDB: Query About + Specs Context
    Agent->>DB: Save Architecture v1
    API-->>Client: Architecture Ready

    Client->>API: POST /projects/{id}/step4
    API->>Agent: Invoke Project Planner
    Agent->>VDB: Query Full Context
    Agent->>DB: Save Plans (overview + N epics) v1
    API-->>Client: Implementation Plans Ready

    Client->>API: POST /projects/{id}/export
    API->>DB: Gather All Documents (About, Specs, Architecture, Plans)
    API-->>Client: Export Ready
    Client->>API: GET /exports/{export_id}
    API-->>Client: ZIP Archive Download
```

## 4) Agent Contracts (Pydantic Models)

Все взаимодействия между агентами типизированы через Pydantic модели, обеспечивающие валидацию данных и автогенерацию документации. Контракты гарантируют согласованность интерфейсов и упрощают тестирование.

### 4.1 Core Data Models

Базовые модели обеспечивают единую структуру данных на всех уровнях системы:

```python
class ProjectContext(BaseModel):
    """Контекст выполнения для всех агентов"""
    tenant_id: str           # Идентификатор арендатора
    project_id: str          # Идентификатор проекта
    current_step: int        # Текущий этап (1-4)
    correlation_id: str      # ID для трассировки запросов
    language: str = "en"     # Язык генерируемых документов

class BusinessAnalystInput(BaseModel):
    """Входные данные для Business Analyst агента"""
    idea_description: str                    # Исходное описание идеи
    user_clarifications: Optional[Dict[str, Any]] = None  # Уточнения от пользователя
    target_audience: Optional[str] = None    # Целевая аудитория

class BusinessAnalystOutput(BaseModel):
    """Результат работы Business Analyst агента"""
    description_document: str               # Сгенерированный документ
    key_facts: List[str]                   # Ключевые факты для индексации
    confidence_score: float                # Уверенность в качестве (0-1)
    validation_checklist: Dict[str, bool]  # Чеклист заполненности разделов
    suggested_questions: List[str]         # Предложенные вопросы для уточнения
```

### 4.2 Agent Interface Contract

Абстрактный базовый класс определяет единый интерфейс для всех агентов:

```python
class AgentBase(ABC):
    """Базовый класс для всех агентов системы"""

    @abstractmethod
    async def process(
        self,
        context: ProjectContext,
        input_data: BaseModel
    ) -> BaseModel:
        """Основная логика обработки запроса агентом"""
        pass

    @abstractmethod
    async def validate_output(self, output: BaseModel) -> ValidationResult:
        """Валидация результата перед сохранением"""
        pass

    @abstractmethod
    def get_system_prompt(self, context: ProjectContext) -> str:
        """Генерация system prompt с учетом контекста"""
        pass
```

## 5) Database Schema

Реляционная схема PostgreSQL оптимизирована для версионирования документов, audit trail агентов и мультитенантной изоляции. Все таблицы включают поле tenant_id для эффективной фильтрации.

### 5.1 Entity Relationship Diagram

```mermaid
erDiagram
    PROJECTS {
        uuid id PK
        string tenant_id
        string name
        string status
        int current_step
        string language
        timestamp created_at
        timestamp updated_at
    }

    DOCUMENT_VERSIONS {
        uuid id PK
        uuid project_id FK
        string document_type
        int version
        text content
        jsonb metadata
        uuid created_by
        timestamp created_at
    }

    AGENT_EXECUTIONS {
        uuid id PK
        uuid project_id FK
        string agent_type
        uuid correlation_id
        jsonb input_data
        jsonb output_data
        string status
        timestamp started_at
        timestamp completed_at
    }

    USERS {
        uuid id PK
        string tenant_id
        string email
        string name
        jsonb profile_data
        timestamp created_at
        timestamp last_login_at
    }

    EXPORTS {
        uuid id PK
        uuid project_id FK
        string status
        string file_path
        jsonb manifest
        timestamp created_at
        timestamp expires_at
    }

    PROJECTS ||--o{ DOCUMENT_VERSIONS : "has versions"
    PROJECTS ||--o{ AGENT_EXECUTIONS : "has executions"
    PROJECTS ||--o{ EXPORTS : "has exports"
    USERS ||--o{ PROJECTS : "owns"
```

### 5.2 Core Tables SQL

```sql
-- Users table for authentication and tenant mapping
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    profile_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP
);

-- Projects table with multi-tenancy and language support
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    current_step INTEGER DEFAULT 1 CHECK (current_step BETWEEN 1 AND 4),
    language VARCHAR(10) DEFAULT 'en' NOT NULL, -- ISO 639-1 language code
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Document versions for full versioning support
CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL, -- 'about', 'architecture', 'specs', 'plan_overview', 'epic_01_infrastructure', 'epic_NN_feature_name', 'epic_final_testing'
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent execution audit trail
CREATE TABLE agent_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL, -- 'business_analyst', 'solution_architect', etc.
    correlation_id UUID NOT NULL,
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Export tracking for download management
CREATE TABLE exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    file_path TEXT,
    manifest JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours')
);
```

### 5.3 Indexing Strategy

Индексы оптимизированы для типичных запросов с учетом мультитенантности и версионирования:

```sql
-- Tenant isolation indexes for fast filtering
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_projects_tenant ON projects(tenant_id);
CREATE INDEX idx_projects_tenant_created ON projects(tenant_id, created_at DESC);

-- Document versioning indexes
CREATE INDEX idx_documents_project_type ON document_versions(project_id, document_type);
CREATE INDEX idx_documents_project_version ON document_versions(project_id, version DESC);
CREATE INDEX idx_documents_created ON document_versions(created_at DESC);

-- Agent execution tracking indexes
CREATE INDEX idx_executions_project ON agent_executions(project_id, started_at DESC);
CREATE INDEX idx_executions_correlation ON agent_executions(correlation_id);
CREATE INDEX idx_executions_status ON agent_executions(status, started_at);

-- Export management indexes
CREATE INDEX idx_exports_project ON exports(project_id);
CREATE INDEX idx_exports_expires ON exports(expires_at) WHERE status = 'completed';

-- Composite indexes for complex queries
CREATE INDEX idx_projects_user_status ON projects(created_by, status, updated_at DESC);
CREATE UNIQUE INDEX idx_documents_unique_version ON document_versions(project_id, document_type, version);
```

## 6) Security Requirements

Безопасность реализована на принципах defense-in-depth с множественными уровнями защиты, начиная от network security до application-level controls.

### 6.1 Authentication & Authorization

Многоуровневая система аутентификации и авторизации с поддержкой современных стандартов:

- **OAuth2 Implementation:** JWT tokens с refresh механизмом, поддержка multiple providers (Google, GitHub)
- **Role-based Access Control (RBAC):**
  - `owner` — полные права на проект включая удаление и управление доступом
  - `editor` — создание и редактирование документов, запуск агентов
  - `viewer` — только чтение документов и просмотр прогресса
- **API Rate Limiting:** адаптивные лимиты по пользователю (1000 req/hour), проекту (500 req/hour) и IP (100 req/min) с использованием Redis для distributed rate limiting
- **Security Middleware Stack:** FastAPI middleware для CORS, security headers, request validation и input sanitization
- **Session Management:** secure cookie handling, automatic session expiration, concurrent session limits

### 6.2 Data Isolation

Строгая изоляция данных предотвращает cross-tenant и cross-project утечки:

- **Tenant Isolation:** принудительная фильтрация по tenant_id на всех уровнях (DB, Vector DB, Cache)
- **Project Scoping:** агенты имеют доступ только к данным текущего проекта через server-side контексты
- **Server-side Filtering:** все запросы к Qdrant автоматически включают tenant/project фильтры, невозможность обхода с клиента
- **Database RLS:** Row Level Security policies в PostgreSQL для дополнительной защиты — автоматическая фильтрация данных на уровне БД
- **Circuit Breaker Pattern:** защита от каскадных сбоев при взаимодействии с внешними LLM API с использованием Tenacity

### 6.3 Privacy & Compliance

Соответствие современным требованиям по защите данных и приватности:

- **Data Encryption:** TLS 1.3 для всех соединений, AES-256 для sensitive данных в БД, encrypted backups
- **Audit Logging:** детальный лог всех действий пользователей с correlation ID для трассировки
- **Data Retention:** автоматическое удаление логов через 90 дней, user data retention policies
- **Secrets Management:** HashiCorp Vault для безопасного хранения API ключей, паролей и сертификатов с автоматической ротацией — open-source решение для централизованного управления секретами без vendor lock-in
- **GDPR Compliance:** право на забвение, data portability, consent management

## 7) Performance Requirements

Производительность критична для user experience, особенно учитывая длительность LLM операций. Система спроектирована для поддержания низких latencies при масштабировании.

### 7.1 Response Time SLOs

Целевые показатели производительности для различных типов операций:

- **Document Generation:** P95 ≤ 30 секунд для базового объема (до 500 слов описания)
- **API Response Time:** P95 ≤ 500ms для CRUD операций (проекты, пользователи)
- **Vector Search:** P95 ≤ 200ms для семантического поиска в контексте проекта
- **SSE Latency:** ≤ 100ms для доставки progress updates от агентов
- **Database Queries:** P95 ≤ 50ms для indexed queries, P95 ≤ 200ms для complex joins

### 7.2 Throughput Requirements

Пропускная способность системы для различных нагрузочных сценариев:

- **Concurrent Users:** поддержка 100+ одновременных активных пользователей в MVP
- **Agent Parallelism:** до 5 одновременных agent executions на проект для избежания resource conflicts
- **Embedding Queue:** обработка до 1000 текстовых фрагментов в минуту через батчинг
- **API Throughput:** 10,000+ requests per minute с горизонтальным масштабированием

### 7.3 Scalability Strategy

Архитектура масштабирования предусматривает как вертикальный, так и горизонтальный рост:

- **Horizontal Scaling:** stateless FastAPI сервисы за load balancer с auto-scaling по CPU/memory
- **Database Scaling:** read replicas для PostgreSQL, возможность шардинга по tenant_id
- **Qdrant Scaling:** кластерное развертывание с добавлением узлов, custom sharding для enterprise клиентов
- **Redis Clustering:** Redis Cluster для высоконагруженных cache/queue сценариев
- **CDN Integration:** статические ассеты и экспортированные архивы через CloudFront/CloudFlare

## 8) Reliability & Observability

Надежность системы обеспечивается через множественные механизмы fault tolerance, comprehensive monitoring и structured logging для быстрой диагностики проблем.

### 8.1 Error Handling & Resilience

Система спроектирована для graceful degradation при различных типах сбоев:

- **Graceful Degradation:** fallback на simplified templates при недоступности агентов, cached responses для критических endpoints
- **Retry Logic:** Tenacity library с экспоненциальным backoff и jitter для внешних LLM API (3 попытки с 1s, 4s, 16s delays)
- **Circuit Breakers:** Tenacity circuit breaker с автоматическим отключением недоступных сервисов на 30-300 секунд для предотвращения каскадных сбоев
- **Distributed Tracing:** OpenTelemetry с автоматической инструментацией FastAPI для сквозной трассировки запросов и correlation IDs
- **Automatic Instrumentation:** OpenTelemetry auto-instrumentation для HTTP requests, database queries, и agent executions
- **Health Checks:** liveness/readiness probes для всех сервисов с автоматическим restart при сбоях

### 8.2 Monitoring & Alerting

Comprehensive мониторинг всех аспектов системы с proactive alerting:

**Key Performance Indicators:**

- API request latency (P50, P95, P99) и error rates по endpoints
- Agent execution success/failure rates с детализацией по типу агента
- Document generation completion rates и среднее время выполнения
- Vector search performance и hit rates в Qdrant
- Queue depth и processing rates для embedding operations
- Database connection pool utilization и query performance
- Resource utilization (CPU, memory, disk) по всем сервисам

**Alerting Thresholds:**

- P95 latency > 30s для document generation
- Error rate > 5% за 5-минутный период
- Queue depth > 1000 items
- Database connection pool > 80% utilization

### 8.3 Structured Logging Strategy

Единый формат логирования обеспечивает легкую агрегацию и анализ:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant_acme_corp",
  "project_id": "proj_456789",
  "user_id": "user_123456",
  "component": "business_analyst_agent",
  "operation": "document_generation",
  "message": "Document generation completed successfully",
  "metrics": {
    "duration_ms": 15000,
    "token_count": 2500,
    "llm_provider": "openai",
    "model": "gpt-4"
  },
  "metadata": {
    "document_type": "description",
    "version": 1,
    "language": "en"
  }
}
```

## 9) Quality Assurance

Качество генерируемых документов обеспечивается через многоуровневую систему валидации, от structure compliance до semantic consistency checks.

### 9.1 Agent Output Validation

Каждый агент включает built-in валидацию результатов перед сохранением:

```python
class ValidationRules:
    """Правила валидации для различных типов документов"""

    def validate_description(self, doc: str) -> ValidationResult:
        """Проверка полноты Project Description"""
        checks = [
            self.has_problem_statement(),      # Описание проблемы
            self.has_target_audience(),        # Целевая аудитория
            self.has_success_metrics(),        # Метрики успеха
            self.has_constraints(),            # Ограничения и риски
            self.has_monetization_model()      # Модель монетизации
        ]
        return ValidationResult(
            passed=all(checks),
            details=checks,
            score=sum(checks) / len(checks)
        )

    def validate_architecture(self, doc: str) -> ValidationResult:
        """Проверка Architecture документа"""
        checks = [
            self.has_technology_stack(),       # Технологический стек
            self.has_component_diagram(),      # Диаграмма компонентов
            self.has_trade_offs_analysis(),    # Анализ компромиссов
            self.has_scalability_plan()        # План масштабирования
        ]
        return ValidationResult(passed=all(checks), details=checks)
```

### 9.2 Content Quality Checks

Автоматизированные проверки качества контента на различных уровнях:

- **Template Compliance:** верификация заполнения всех обязательных разделов согласно предустановленным templates
- **Consistency Validation:** cross-document проверка согласованности терминологии, технических решений и временных оценок
- **Hallucination Detection:** анализ противоречий между фактами, несоответствий в технических деталях
- **Language Quality:** базовые грамматические проверки, readability scoring, terminology consistency
- **Completeness Scoring:** количественная оценка полноты документа (0-100%) на основе заполненности ключевых разделов

## 10) Export & Integration

Экспорт документов спроектирован для seamless интеграции с существующими developer workflows и готовности к immediate use в IDE и project management tools.

### 10.1 Document Package Structure

Стандартизированная структура экспортируемого архива следует лучшим практикам startup documentation и PRD (Product Requirements Document) методологии:

```text
project-name/
├── README.md                          # Project overview and quick start guide
└── docs/                             # Main project documents
    ├── about.md                      # Project vision, goals, target audience (PRD style)
    ├── specs.md                      # Engineering standards, DoD, code guidelines
    ├── architecture.md               # Technical architecture and design decisions
    └── plans/                        # Implementation planning
        ├── overview.md               # High-level implementation strategy and roadmap
        ├── 01-infrastructure.md      # Epic 1: Architecture setup with minimal functionality
        ├── 02-authentication.md      # Epic 2: User management and OAuth2 integration
        ├── 03-content-system.md      # Epic 3: Core business logic (project-specific)
        ├── 04-agents.md              # Epic 4: AI agents and document generation
        ├── 05-optimization.md        # Epic 5: Performance, scaling, monitoring
        ├── [N-1]-[feature].md        # Additional feature epics based on project needs
        └── [N]-testing.md            # Final Epic: Comprehensive testing and QA
```

**Document Structure Methodology:**

- **about.md** — follows Lean Startup PRD principles: problem statement, target market, value proposition, success metrics
- **specs.md** — engineering standards document combining coding guidelines, review process, and quality gates, formed based on project description
- **architecture.md** — technical design document in Amazon's 6-page narrative style: context, constraints, options, decision rationale, created considering established standards
- **plans/** — Agile planning with incremental development approach: overview roadmap + variable number of epics for phased functionality growth from minimal architecture to full-featured product

**Epic Planning Principles:**

1. **Epic 1 (Infrastructure)** — always first: architecture setup with all components but minimal functionality (health checks, basic endpoints), implemented according to established standards
2. **Epic 2-(N-2) (Feature Epics)** — phased development by functional areas: authentication → core business logic → specific features, following architectural decisions
3. **Epic N-1 (Optimization)** — performance, monitoring, scaling after core functionality
4. **Epic N (Testing)** — always last: comprehensive project testing, integration testing, load testing, security audit, UAT
5. **Number of epics** — determined by project complexity and can vary from 4-5 to 12+ depending on scope

### 10.2 Document Quality Features

Встроенные инструменты для повышения качества генерируемых документов:

- **Readability Analysis:** textstat для автоматического scoring читаемости документов (Flesch-Kincaid Grade Level, Reading Ease)
- **Grammar Validation:** language-check для проверки грамматики и стилистики на различных языках
- **Markdown Enhancement:** python-markdown с расширениями для Mermaid diagrams, tables, TOC generation
- **Content Consistency:** cross-document терминологическая проверка и ссылочная целостность

### 10.3 Export & Integration Points

Возможности интеграции с внешними системами и workflows:

- **Enhanced Export Formats:**
  - ZIP архивы с оптимизированной структурой для IDE integration
  - PDF generation через weasyprint для presentation-ready documents
  - Word format export для enterprise collaboration workflows
- **Webhook Support:** настраиваемые HTTP callbacks при завершении генерации, поддержка Slack/Discord/Teams notifications
- **REST API for External Tools:** открытый API для интеграции с CI/CD pipelines, project management tools
- **Git Integration (Future):** автоматический commit сгенерированных документов в указанный репозиторий
- **Template Customization (Future):** пользовательские шаблоны документов для specific domain requirements

## 11) Development & Deployment

### 11.1 Local Development Port Scheme

Для удобства локальной разработки используется систематизированная схема портов:

| Сервис     | Внешний порт | Внутренний порт | URL для доступа       |
| ---------- | ------------ | --------------- | --------------------- |
| Frontend   | 5200         | 5200            | <http://localhost:5200> |
| API        | 5210         | 8000            | <http://localhost:5210> |
| PostgreSQL | 5220         | 5432            | localhost:5220        |
| Qdrant     | 5230         | 6333            | <http://localhost:5230> |
| Redis      | 5240         | 6379            | localhost:5240        |
| Vault      | 5250         | 8200            | <http://localhost:5250> |

**Преимущества схемы:**

- Легко запомнить: 52XX порты для всех сервисов
- Логическая последовательность: Frontend → API → Data services
- Избежание конфликтов с системными портами
- Удобство для development tools и debugging

### 11.2 Docker Architecture Diagram

```mermaid
graph TB
    subgraph "Host Machine (localhost)"
        DEV[Developer]
        BROWSER[Web Browser<br/>:5200]
        API_CLIENT[API Client<br/>:5210]
        DB_CLIENT[DB Client<br/>:5220]
        QDRANT_UI[Qdrant Web UI<br/>:5230]
        REDIS_CLI[Redis CLI<br/>:5240]
        VAULT_UI[Vault Web UI<br/>:5250]
    end

    subgraph "Docker Network"
        subgraph "Frontend Container"
            FRONTEND[React App<br/>:3000]
        end

        subgraph "Backend Container"
            API[FastAPI<br/>:8000]
        end

        subgraph "Infrastructure Containers"
            POSTGRES[PostgreSQL<br/>:5432]
            QDRANT[Qdrant<br/>:6333]
            REDIS[Redis<br/>:6379]
            VAULT[HashiCorp Vault<br/>:8200]
        end

        subgraph "Volumes"
            PG_VOL[(postgres_data)]
            QD_VOL[(qdrant_data)]
            RD_VOL[(redis_data)]
            VT_VOL[(vault_data)]
        end
    end

    %% External connections
    DEV --> BROWSER
    DEV --> API_CLIENT
    DEV --> DB_CLIENT
    DEV --> QDRANT_UI
    DEV --> REDIS_CLI
    DEV --> VAULT_UI

    %% Port mappings
    BROWSER -.5200:3000.-> FRONTEND
    API_CLIENT -.5210:8000.-> API
    DB_CLIENT -.5220:5432.-> POSTGRES
    QDRANT_UI -.5230:6333.-> QDRANT
    REDIS_CLI -.5240:6379.-> REDIS
    VAULT_UI -.5250:8200.-> VAULT

    %% Internal container connections
    FRONTEND --> API
    API --> POSTGRES
    API --> QDRANT
    API --> REDIS
    API --> VAULT

    %% Volume mounts
    POSTGRES -.-> PG_VOL
    QDRANT -.-> QD_VOL
    REDIS -.-> RD_VOL
    VAULT -.-> VT_VOL

    %% Styling
    classDef containerStyle fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef volumeStyle fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef hostStyle fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px

    class FRONTEND,API,POSTGRES,QDRANT,REDIS,VAULT containerStyle
    class PG_VOL,QD_VOL,RD_VOL,VT_VOL volumeStyle
    class BROWSER,API_CLIENT,DB_CLIENT,QDRANT_UI,REDIS_CLI,VAULT_UI hostStyle
```

### 11.3 Environment Configuration

```yaml
# docker-compose.yml structure
# Port mapping scheme: Frontend:5200, API:5210, Infrastructure services:5220+
services:
  frontend:
    build: ./frontend
    ports: ["5200:3000"] # Frontend доступен на localhost:5200

  api:
    build: ./backend
    ports: ["5210:8000"] # API доступно на localhost:5210
    environment:
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/jeex_plan
      - QDRANT_URL=http://qdrant:6333
      - REDIS_URL=redis://redis:6379
      - VAULT_ADDR=http://vault:8200
    depends_on:
      - postgres
      - qdrant
      - redis
      - vault

  postgres:
    image: postgres:18-alpine
    ports: ["5220:5432"] # PostgreSQL доступен на localhost:5220
    environment:
      - POSTGRES_DB=jeex_plan
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=secure_password
    volumes: ["./postgres_data:/var/lib/postgresql/data"]

  qdrant:
    image: qdrant/qdrant:v1.15.4
    ports: ["5230:6333"] # Qdrant доступен на localhost:5230
    volumes: ["./qdrant_data:/qdrant/storage"]

  redis:
    image: redis:8.2-alpine
    ports: ["5240:6379"] # Redis доступен на localhost:5240
    volumes: ["./redis_data:/data"]

  vault:
    image: vault:1.15.4
    ports: ["5250:8200"] # Vault доступен на localhost:5250
    cap_add: ["IPC_LOCK"]
    environment:
      - VAULT_DEV_ROOT_TOKEN_ID=dev-token
      - VAULT_DEV_LISTEN_ADDRESS=0.0.0.0:8200
    volumes: ["./vault_data:/vault/data"]
```

### 11.4 Testing Strategy

- **Unit Tests:** для агентов и core бизнес-логики
- **Integration Tests:** полные user flows через API
- **Load Testing:** производительность при нагрузке
- **Security Testing:** проверка изоляции тенантов
- **Contract Testing:** валидация Pydantic схем между компонентами

### 11.5 CI/CD Pipeline

```yaml
stages:
  - lint: black, flake8, mypy для Python; eslint, prettier для TS
  - test: pytest для backend, jest для frontend
  - security: dependency scanning, secret detection
  - build: Docker images
  - deploy: staging -> production с blue-green deployment
```

## 12) Limits & Quotas

### 12.1 Resource Limits

```python
class TenantLimits:
    max_projects_active: int = 10
    max_documents_per_project: int = 100
    max_embedding_points: int = 50000
    max_api_requests_per_hour: int = 1000
    max_concurrent_generations: int = 3
```

### 12.2 Fair Usage Policy

- **Rate Limiting:** по IP, по пользователю, по тенанту
- **Queue Priority:** FIFO с anti-starvation механизмами
- **Resource Cleanup:** автоматическое удаление старых временных данных
- **Abuse Detection:** мониторинг подозрительной активности

---

**Ссылки на дополнительную документацию:**

- [Qdrant Multi-tenancy Best Practices](https://medium.com/qdrant/the-tao-of-qdrant-multi-tenancy-162c71f830fb)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [CrewAI Framework](https://github.com/joaomdmoura/crewAI)
- [Pydantic AI](https://github.com/pydantic/pydantic-ai)
