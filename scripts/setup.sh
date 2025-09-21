#!/bin/bash

# JEEX Plan Development Setup Script
# Sets up the development environment

set -e

echo "🚀 Setting up JEEX Plan development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/uploads backend/exports
mkdir -p postgres_data qdrant_data redis_data vault_data

# Copy environment files
echo "📋 Setting up environment files..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
fi

if [ ! -f frontend/.env ]; then
    cp frontend/.env.example frontend/.env
    echo "✅ Created frontend/.env"
fi

# Build and start services
echo "🏗️ Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Run database initialization
echo "🗄️ Initializing database..."
docker-compose exec -T postgres psql -U postgres -d jeex_plan -f /docker-entrypoint-initdb.d/init-db.sql

echo "✅ Database initialized"

# Show service status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 JEEX Plan development environment is ready!"
echo ""
echo "📱 Frontend: http://localhost:5200"
echo "🔧 API: http://localhost:5210"
echo "📖 API Docs: http://localhost:5210/docs"
echo ""
echo "🗄️ Database: localhost:5220"
echo "🔍 Qdrant: http://localhost:5230"
echo "⚡ Redis: localhost:5240"
echo "🔐 Vault: http://localhost:5250"
echo ""
echo "🛠️ Development Tools:"
echo "   pgAdmin: http://localhost:8080 (admin/admin)"
echo "   Qdrant UI: http://localhost:6333"
echo ""
echo "📝 To stop services: docker-compose down"
echo "🔄 To restart: docker-compose restart"
echo "📊 To view logs: docker-compose logs -f [service]"