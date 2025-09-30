#!/bin/sh
# Redis startup script with password configuration

# Start Redis with password from environment variable
exec redis-server --requirepass "${REDIS_PASSWORD}" --include /etc/redis/redis.conf