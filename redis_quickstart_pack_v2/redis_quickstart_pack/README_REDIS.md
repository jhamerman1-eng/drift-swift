# Redis Quickstart (single node, dev)

## Start
```powershell
docker compose --env-file .env.redis -f docker-compose.redis.yml up -d
docker exec -it drift-redis redis-cli -a $env:REDIS_PASSWORD ping   # expect PONG
```

## Bot ENV
```
REDIS_URL=redis://:change_me_strong@localhost:6379/0
```
