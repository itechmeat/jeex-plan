# JEEX Plan

> Turn ideas into docs.

JEEX Plan is a multi-agent documentation generation system that transforms raw ideas into professional Markdown documentation packages through AI-powered analysis.

## 🏗️ Architecture Overview

This implementation follows a microservices architecture with the following components:

### Core Services
- **Frontend**: React + TypeScript SPA (Port 5200)
- **API Backend**: FastAPI with Python (Port 5210)
- **PostgreSQL**: Primary database (Port 5220)
- **Qdrant**: Vector database for semantic search (Port 5230)
- **Redis**: Cache and message queue (Port 5240)
- **Vault**: Secrets management (Port 5250)

### Multi-Agent System
- **Business Analyst**: Extracts and structures project requirements
- **Solution Architect**: Designs technical architecture
- **Project Planner**: Creates implementation roadmaps
- **Engineering Standards**: Defines development guidelines

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd jeex-plan
   ```

2. **Run the setup script**
   ```bash
   ./scripts/setup.sh
   ```

3. **Access the application**
   - Frontend: http://localhost:5200
   - API: http://localhost:5210
   - API Documentation: http://localhost:5210/docs

### Manual Setup

1. **Copy environment files**
  ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env
  ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**
   ```bash
   docker-compose exec -T postgres psql -U postgres -d jeex_plan -f /docker-entrypoint-initdb.d/init-db.sql
   ```

## 🛠️ Development

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Backend Development
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Database Migrations
```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## 🏥 Health Checks

Run the health check script to verify all services are running:
```bash
./scripts/health-check.sh
```

Or access individual endpoints:
- API Health: http://localhost:5210/api/v1/health
- Frontend: http://localhost:5200

## 📊 Monitoring

### Service Endpoints
- **Frontend**: http://localhost:5200
- **API**: http://localhost:5210
- **API Docs**: http://localhost:5210/docs
- **Database**: localhost:5220
- **Qdrant**: http://localhost:5230
- **Redis**: localhost:5240
- **Vault**: http://localhost:5250

### Development Tools
- **pgAdmin**: http://localhost:8080 (admin/admin)
- **Qdrant UI**: http://localhost:6333

## 🐳 Docker Commands

### Start all services
```bash
docker-compose up -d
```

### Stop all services
```bash
docker-compose down
```

### View logs
```bash
docker-compose logs -f [service]
```

### Rebuild services
```bash
docker-compose build
```

### Development mode with hot reload
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## 🔧 Configuration

### Environment Variables
See `.env.example` for all available configuration options. Provide real secrets at runtime through Vault or gitignored `.env`/`.env.local` files, and keep helper tooling such as `.claude/settings.local.json` free of credential values.

### Multi-tenancy
The system supports tenant isolation through:
- Database-level separation
- Vector database payload filtering
- Cache key namespacing
- Request context middleware

### Authentication
- JWT-based authentication
- OAuth2 integration points
- Role-based access control (RBAC)

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user info

### Project Management
- `GET /api/v1/` - List projects
- `POST /api/v1/` - Create project
- `GET /api/v1/{project_id}` - Get project details
- `PUT /api/v1/{project_id}` - Update project
- `DELETE /api/v1/{project_id}` - Delete project

### Document Generation
- `POST /api/v1/{project_id}/step1` - Generate description
- `POST /api/v1/{project_id}/step2` - Generate architecture
- `POST /api/v1/{project_id}/step3` - Generate implementation plan
- `POST /api/v1/{project_id}/step4` - Generate standards
- `POST /api/v1/{project_id}/export` - Export documents

### Health Checks
- `GET /api/v1/health` - Comprehensive health check
- `GET /api/v1/health/simple` - Simple health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

## 🔒 Security

### Multi-tenancy
- Strict tenant isolation at all levels
- Server-side payload filtering for vector search
- Database row-level security (optional)
- Cache key namespacing

### Authentication & Authorization
- JWT tokens with refresh mechanism
- OAuth2 provider integration points
- Rate limiting per tenant/project
- API key management

### Data Protection
- TLS encryption for all communications
- Secret management with HashiCorp Vault
- Input validation and sanitization
- Structured logging with sensitive data filtering

## 📈 Monitoring & Observability

### OpenTelemetry
- Distributed tracing across all services
- Metrics collection and export
- Structured logging with correlation IDs

### Health Monitoring
- Service health endpoints
- Database connectivity checks
- Redis and Qdrant connectivity
- Vault secrets management

### Performance
- Response time monitoring
- Error rate tracking
- Resource utilization metrics
- Custom business metrics

## 🚀 Deployment

### Production Considerations
- Use environment-specific configurations
- Enable TLS termination
- Configure proper secrets management
- Set up monitoring and alerting
- Implement backup and disaster recovery

### Infrastructure
- Container orchestration with Kubernetes
- Load balancing and auto-scaling
- Database clustering and read replicas
- CDN for static assets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API documentation at `/docs`

---

**Built with ❤️ for the developer community**
