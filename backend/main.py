"""
JEEX Plan - Simple Main API Service
Упрощенная реализация для Docker контейнера
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import aiohttp
import time
from typing import Dict, Any

app = FastAPI(
    title="JEEX Plan API",
    description="AI-powered система управления документацией",
    version="1.0.0"
)

# Настройка CORS для разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Корневой endpoint"""
    return {
        "service": "JEEX Plan API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "jeex-plan-api",
        "version": "1.0.0",
        "database": "simulated_connected",
        "redis": "simulated_connected",
        "qdrant": "simulated_connected"
    }


@app.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Проверка готовности сервиса"""
    return {
        "status": "ready",
        "database": "simulated_ready",
        "cache": "simulated_ready",
        "vector_db": "simulated_ready"
    }


async def check_service_health(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Проверка здоровья внешнего сервиса"""
    start_time = time.time()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                response_time = round((time.time() - start_time) * 1000)
                if response.status == 200:
                    return {
                        "status": "pass",
                        "response_time": response_time,
                        "details": "Service operational"
                    }
                else:
                    return {
                        "status": "fail",
                        "response_time": response_time,
                        "details": f"HTTP {response.status}"
                    }
    except asyncio.TimeoutError:
        return {
            "status": "fail",
            "response_time": round((time.time() - start_time) * 1000),
            "details": "Timeout"
        }
    except Exception as e:
        return {
            "status": "fail",
            "response_time": round((time.time() - start_time) * 1000),
            "details": str(e)
        }


@app.get("/system/status")
async def system_status() -> Dict[str, Any]:
    """Проверка статуса всех сервисов системы"""
    services = [
        {"name": "API Backend", "endpoint": "http://localhost:8000/health", "url": "http://localhost:8000/health"},
        {"name": "PostgreSQL", "endpoint": "localhost:5432", "url": "http://postgres:5432"},
        {"name": "Qdrant", "endpoint": "http://localhost:6333/", "url": "http://qdrant:6333/"},
        {"name": "Redis", "endpoint": "localhost:6379", "url": "http://redis:6379"},
        {"name": "Vault", "endpoint": "http://localhost:8200/v1/sys/health", "url": "http://vault:8200/v1/sys/health"},
        {"name": "Frontend", "endpoint": "http://localhost:5200", "url": "http://host.docker.internal:5200"}
    ]

    results = []
    for service in services:
        service_name = service["name"]
        check_result = await check_service_health(service["url"])

        results.append({
            "service": service_name,
            "endpoint": service["endpoint"],
            "status": check_result["status"],
            "responseTime": check_result["response_time"],
            "details": check_result["details"],
            "timestamp": time.time()
        })

    return {
        "services": results,
        "timestamp": time.time()
    }


@app.get("/api/v1/info")
async def api_info() -> Dict[str, Any]:
    """Информация об API"""
    return {
        "name": "JEEX Plan API",
        "description": "AI-powered система управления документацией",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "Корневой endpoint"},
            {"path": "/health", "method": "GET", "description": "Проверка здоровья"},
            {"path": "/ready", "method": "GET", "description": "Проверка готовности"},
            {"path": "/system/status", "method": "GET", "description": "Статус всех сервисов"},
            {"path": "/api/v1/info", "method": "GET", "description": "Информация об API"}
        ]
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )