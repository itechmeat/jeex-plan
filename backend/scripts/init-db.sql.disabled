-- JEEX Plan Database Initialization Script
-- Creates initial database structure for MVP

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

-- Create projects table with multi-tenancy support
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',
    current_step INTEGER DEFAULT 1 CHECK (current_step BETWEEN 1 AND 4),
    language VARCHAR(10) DEFAULT 'en',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Create document versions table for versioning support
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    document_type VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique versions per document type per project
    UNIQUE(project_id, document_type, version)
);

-- Create agent executions table for audit trail
CREATE TABLE IF NOT EXISTS agent_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    correlation_id UUID NOT NULL,
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Create exports table for download management
CREATE TABLE IF NOT EXISTS exports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending',
    file_path TEXT,
    manifest JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '24 hours'),
    downloaded_at TIMESTAMP
);

-- Create tenant settings table for multi-tenancy configuration
CREATE TABLE IF NOT EXISTS tenant_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create rate limiting table
CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) NOT NULL,
    count INTEGER DEFAULT 0,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    window_size INTEGER NOT NULL,
    "limit" INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique keys for active windows
    UNIQUE(key, window_start)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_projects_tenant ON projects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_projects_tenant_created ON projects(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_documents_project_type ON document_versions(project_id, document_type);
CREATE INDEX IF NOT EXISTS idx_documents_project_version ON document_versions(project_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_executions_project ON agent_executions(project_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_executions_correlation ON agent_executions(correlation_id);
CREATE INDEX IF NOT EXISTS idx_executions_status ON agent_executions(status, started_at);
CREATE INDEX IF NOT EXISTS idx_exports_project ON exports(project_id);
CREATE INDEX IF NOT EXISTS idx_exports_expires ON exports(expires_at) WHERE status = 'completed';
CREATE INDEX IF NOT EXISTS idx_rate_limits_key_window ON rate_limits(key, window_start);
CREATE INDEX IF NOT EXISTS idx_projects_deleted ON projects(deleted_at) WHERE deleted_at IS NOT NULL;

-- Create composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_projects_user_status ON projects(created_by, status, updated_at DESC);

-- Insert default tenant settings
INSERT INTO tenant_settings (tenant_id, settings) VALUES
('default', '{"max_projects": 10, "max_documents_per_project": 100, "enable_ai_features": true}')
ON CONFLICT (tenant_id) DO UPDATE SET settings = EXCLUDED.settings;

-- Create default admin user (for development only)
INSERT INTO users (tenant_id, email, name, password_hash) VALUES
('default', 'admin@jeex.plan', 'Admin User', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeZeUfkZMBs9kYZP6')  -- password: admin123
ON CONFLICT (email) DO NOTHING;

-- Create sample project for development
INSERT INTO projects (tenant_id, name, created_by) VALUES
('default', 'JEEX Plan Infrastructure', (SELECT id FROM users WHERE email = 'admin@jeex.plan'))
ON CONFLICT DO NOTHING;

-- Create triggers for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_settings_updated_at BEFORE UPDATE ON tenant_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();