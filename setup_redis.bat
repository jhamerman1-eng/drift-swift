@echo off
REM Redis Setup Script for Drift Trading Bot (Windows)
REM This script sets up Redis for production caching

echo 🚀 Setting up Redis for Drift Trading Bot...

REM Check if Docker is available
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker is not installed. Please install Docker first.
    echo Visit: https://docs.docker.com/get-docker/
    pause
    exit /b 1
)

REM Create Redis data directory
if not exist "redis-data" mkdir redis-data

REM Create Redis configuration
echo # Redis configuration for Drift trading bot > redis.conf
echo bind 127.0.0.1 >> redis.conf
echo port 6379 >> redis.conf
echo timeout 0 >> redis.conf
echo tcp-keepalive 300 >> redis.conf
echo daemonize no >> redis.conf
echo supervised no >> redis.conf
echo loglevel notice >> redis.conf
echo logfile "" >> redis.conf
echo. >> redis.conf
echo # Persistence >> redis.conf
echo save 900 1 >> redis.conf
echo save 300 10 >> redis.conf
echo save 60 10000 >> redis.conf
echo. >> redis.conf
echo # Memory management >> redis.conf
echo maxmemory 256mb >> redis.conf
echo maxmemory-policy allkeys-lru >> redis.conf
echo. >> redis.conf
echo # Disable dangerous commands >> redis.conf
echo rename-command FLUSHDB "" >> redis.conf
echo rename-command FLUSHALL "" >> redis.conf
echo rename-command SHUTDOWN SHUTDOWN_REDIS >> redis.conf

echo ✅ Redis configuration created

REM Create docker-compose file for Redis
echo version: '3.8' > docker-compose.redis.yml
echo services: >> docker-compose.redis.yml
echo   redis: >> docker-compose.redis.yml
echo     image: redis:7-alpine >> docker-compose.redis.yml
echo     container_name: drift-redis >> docker-compose.redis.yml
echo     restart: unless-stopped >> docker-compose.redis.yml
echo     ports: >> docker-compose.redis.yml
echo       - "6379:6379" >> docker-compose.redis.yml
echo     volumes: >> docker-compose.redis.yml
echo       - ./redis-data:/data >> docker-compose.redis.yml
echo       - ./redis.conf:/etc/redis/redis.conf >> docker-compose.redis.yml
echo     command: redis-server /etc/redis/redis.conf >> docker-compose.redis.yml
echo     healthcheck: >> docker-compose.redis.yml
echo       test: ["CMD", "redis-cli", "ping"] >> docker-compose.redis.yml
echo       interval: 10s >> docker-compose.redis.yml
echo       timeout: 3s >> docker-compose.redis.yml
echo       retries: 5 >> docker-compose.redis.yml
echo. >> docker-compose.redis.yml
echo   redis-insight: >> docker-compose.redis.yml
echo     image: redis/redisinsight:latest >> docker-compose.redis.yml
echo     container_name: drift-redis-insight >> docker-compose.redis.yml
echo     restart: unless-stopped >> docker-compose.redis.yml
echo     ports: >> docker-compose.redis.yml
echo       - "5540:5540" >> docker-compose.redis.yml
echo     depends_on: >> docker-compose.redis.yml
echo       - redis >> docker-compose.redis.yml

echo ✅ Docker Compose configuration created

REM Start Redis
echo 🐳 Starting Redis with Docker...
docker-compose -f docker-compose.redis.yml up -d

REM Wait for Redis to be ready
echo ⏳ Waiting for Redis to start...
timeout /t 5 /nobreak >nul

REM Test Redis connection
docker exec drift-redis redis-cli ping | findstr "PONG" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Redis is running and responding to ping
) else (
    echo ❌ Redis failed to start properly
    pause
    exit /b 1
)

REM Test basic Redis operations
echo 🧪 Testing Redis functionality...
docker exec drift-redis redis-cli SET test_key "Hello from Drift Redis!" >nul
docker exec drift-redis redis-cli GET test_key | findstr "Hello from Drift Redis!" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Redis SET/GET operations working
)
docker exec drift-redis redis-cli DEL test_key >nul

echo.
echo 🎉 Redis setup completed successfully!
echo.
echo 📊 Redis Dashboard:
echo    Web UI: http://localhost:5540
echo    Connection: redis://localhost:6379
echo.
echo 📝 Useful commands:
echo    docker-compose -f docker-compose.redis.yml logs -f redis    # View logs
echo    docker exec -it drift-redis redis-cli                     # Connect to Redis CLI
echo    docker-compose -f docker-compose.redis.yml down            # Stop Redis
echo.
echo ⚙️  Configuration:
echo    - Max memory: 256MB
echo    - Persistence: Enabled (save every 15min if 1+ keys changed)
echo    - LRU eviction policy
echo    - Dangerous commands disabled for security
echo.
pause

