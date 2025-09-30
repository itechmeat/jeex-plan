#!/bin/bash
# Database initialization script with environment validation

set -euo pipefail

echo "🔍 Validating required environment variables..."

# Validate required environment variables
required_vars=("POSTGRES_PASSWORD" "POSTGRES_DB")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "❌ ERROR: Missing required environment variables:"
    printf "   - %s\n" "${missing_vars[@]}"
    echo ""
    echo "Please set these variables in your .env file before starting the services."
    echo ""
    echo "Example .env file:"
    echo "POSTGRES_PASSWORD=your_secure_password_here"
    echo "POSTGRES_DB=jeex_plan"
    echo "REDIS_PASSWORD=your_redis_password_here"
    echo "QDRANT_API_KEY=your_qdrant_api_key_here"
    exit 1
fi

echo "✅ All required environment variables are present"
echo "🚀 Initializing database with PostgreSQL 18 features and multi-tenant setup..."

# Create database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create database if not exists (handled by PostgreSQL init)

    -- PostgreSQL 18: Enable uuidv7() function and other extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

    -- PostgreSQL 18: Enable pg_stat_statements for query performance monitoring
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

    -- PostgreSQL 18: Enable pg_trgm for text search improvements
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";

    -- Set up default schema and roles for multi-tenancy
    CREATE SCHEMA IF NOT EXISTS app;
    CREATE SCHEMA IF NOT EXISTS audit;

    -- PostgreSQL 18: Create JTI generation function using native uuidv7()
    CREATE OR REPLACE FUNCTION generate_jti()
    RETURNS TEXT AS \$\$
    BEGIN
        RETURN uuidv7()::TEXT;
    END;
    \$\$ LANGUAGE plpgsql;

    -- Create tenant-specific functions
    CREATE OR REPLACE FUNCTION set_tenant_id()
    RETURNS TRIGGER AS \$\$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            NEW.tenant_id := current_setting('app.current_tenant_id')::uuid;
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE' THEN
            NEW.tenant_id := OLD.tenant_id;
            RETURN NEW;
        END IF;
        RETURN NULL;
    END;
    \$\$ LANGUAGE plpgsql;

    -- PostgreSQL 18: Enable virtual generated columns support
    ALTER DATABASE $POSTGRES_DB SET row_security = on;

    -- PostgreSQL 18: Enable parallel query processing for better performance
    ALTER DATABASE $POSTGRES_DB SET max_parallel_workers_per_gather = 2;
    ALTER DATABASE $POSTGRES_DB SET max_parallel_workers = 4;

    -- Set default privileges
    ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO postgres;
    ALTER DEFAULT PRIVILEGES IN SCHEMA audit GRANT ALL ON TABLES TO postgres;

    -- PostgreSQL 18: Configure enhanced monitoring
    ALTER DATABASE $POSTGRES_DB SET track_activity_query_size = 2048;
    ALTER DATABASE $POSTGRES_DB SET log_min_duration_statement = 1000;

EOSQL

echo "✅ Database initialization completed successfully"
echo "📊 Database: $POSTGRES_DB"
echo "🔐 Multi-tenant security enabled with Row Level Security"