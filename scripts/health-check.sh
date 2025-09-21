#!/bin/bash

# JEEX Plan Health Check Script
# Checks the health of all services

set -e

echo "🏥 JEEX Plan Health Check"
echo "========================"

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}

    echo -n "🔍 Checking $service_name... "

    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

# Function to check database
check_database() {
    echo -n "🗄️ Checking PostgreSQL... "

    if docker-compose exec -T postgres pg_isready -U postgres -d jeex_plan > /dev/null 2>&1; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

# Function to check Redis
check_redis() {
    echo -n "⚡ Checking Redis... "

    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

# Function to check Qdrant
check_qdrant() {
    echo -n "🔍 Checking Qdrant... "

    if curl -s -f "$QDRANT_URL/" > /dev/null 2>&1; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

# Function to check Vault
check_vault() {
    echo -n "🔐 Checking Vault... "

    if curl -s -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        echo "✅ Healthy"
        return 0
    else
        echo "❌ Unhealthy"
        return 1
    fi
}

# Main health check
main() {
    # Set service URLs
    API_URL="http://localhost:5210"
    FRONTEND_URL="http://localhost:5200"
    QDRANT_URL="http://localhost:5230"
    VAULT_ADDR="http://localhost:5250"

    echo "🔗 Service URLs:"
    echo "   API: $API_URL"
    echo "   Frontend: $FRONTEND_URL"
    echo "   Qdrant: $QDRANT_URL"
    echo "   Vault: $VAULT_ADDR"
    echo ""

    # Check services
    HEALTHY_SERVICES=0
    TOTAL_SERVICES=5

    # Check Frontend
    if check_service "Frontend" "$FRONTEND_URL"; then
        ((HEALTHY_SERVICES++))
    fi

    # Check API
    if check_service "API" "$API_URL/api/v1/health" "200"; then
        ((HEALTHY_SERVICES++))
    fi

    # Check Database
    if check_database; then
        ((HEALTHY_SERVICES++))
    fi

    # Check Redis
    if check_redis; then
        ((HEALTHY_SERVICES++))
    fi

    # Check Qdrant
    if check_qdrant; then
        ((HEALTHY_SERVICES++))
    fi

    # Check Vault
    if check_vault; then
        ((HEALTHY_SERVICES++))
    fi

    # Summary
    echo ""
    echo "📊 Health Summary:"
    echo "   Healthy Services: $HEALTHY_SERVICES/$TOTAL_SERVICES"

    if [ $HEALTHY_SERVICES -eq $TOTAL_SERVICES ]; then
        echo "🎉 All services are healthy!"
        exit 0
    else
        echo "⚠️  Some services are unhealthy. Check logs for details:"
        echo "   docker-compose logs [service]"
        exit 1
    fi
}

# Run main function
main "$@"