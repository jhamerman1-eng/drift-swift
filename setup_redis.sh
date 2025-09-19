#!/bin/bash
# Redis Setup Script for Drift Trading Bot
# This script sets up Redis for production caching

set -e

echo "🚀 Setting up Redis for Drift Trading Bot..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Create Redis data directory
REDIS_DATA_DIR="./redis-data"
mkdir -p "$REDIS_DATA_DIR"

# Create Redis configuration
cat > redis.conf << EOF
# Redis configuration for Drift trading bot
bind 127.0.0.1
port 6379
timeout 0
tcp-keepalive 300
daemonize no
supervised no
loglevel notice
logfile ""

# Persistence
save 900 1
save 300 10
save 60 10000

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command SHUTDOWN SHUTDOWN_REDIS
EOF

echo "✅ Redis configuration created"

# Create docker-compose file for Redis
cat > docker-compose.redis.yml << EOF
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    container_name: drift-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - ./redis-data:/data
      - ./redis.conf:/etc/redis/redis.conf
    command: redis-server /etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  redis-insight:
    image: redis/redisinsight:latest
    container_name: drift-redis-insight
    restart: unless-stopped
    ports:
      - "5540:5540"
    depends_on:
      - redis
EOF

echo "✅ Docker Compose configuration created"

# Start Redis
echo "🐳 Starting Redis with Docker..."
docker-compose -f docker-compose.redis.yml up -d

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to start..."
sleep 5

# Test Redis connection
if docker exec drift-redis redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is running and responding to ping"
else
    echo "❌ Redis failed to start properly"
    exit 1
fi

# Test basic Redis operations
echo "🧪 Testing Redis functionality..."
docker exec drift-redis redis-cli SET test_key "Hello from Drift Redis!" > /dev/null
docker exec drift-redis redis-cli GET test_key | grep -q "Hello from Drift Redis!" && echo "✅ Redis SET/GET operations working"
docker exec drift-redis redis-cli DEL test_key > /dev/null

echo ""
echo "🎉 Redis setup completed successfully!"
echo ""
echo "📊 Redis Dashboard:"
echo "   Web UI: http://localhost:5540"
echo "   Connection: redis://localhost:6379"
echo ""
echo "📝 Useful commands:"
echo "   docker-compose -f docker-compose.redis.yml logs -f redis    # View logs"
echo "   docker exec -it drift-redis redis-cli                     # Connect to Redis CLI"
echo "   docker-compose -f docker-compose.redis.yml down            # Stop Redis"
echo ""
echo "⚙️  Configuration:"
echo "   - Max memory: 256MB"
echo "   - Persistence: Enabled (save every 15min if 1+ keys changed)"
echo "   - LRU eviction policy"
echo "   - Dangerous commands disabled for security"

