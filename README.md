# mcp-server

A Model Context Protocol (MCP) server

## Архитектура

```
┌──────────────────────────────────────────┐
│          OpenWebUI (порт 3000)           │
└────────────────┬─────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ MCPO (8081)   │
         └───────┬───────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ db_connector │  │ csv_loader   │
│  (порт 8001) │  │ (порт 8002)  │
└──────────────┘  └──────────────┘
   PostgreSQL       DuckDB (CSV)
   ClickHouse       + Plotly
```

## Быстрый запуск

### 1. Установка зависимостей

```bash
# Для обоих серверов
uv sync --all-extras

# Или только для csv_loader
uv sync --extra csv_loader
```

### 2. Запуск в Docker

```bash
# Собрать образ (общий для обоих серверов)
docker-compose build mcp-server-db-connector

# Запустить оба MCP сервера
docker-compose up mcp-server-db-connector mcp-server-csv-loader

# Запустить всю инфраструктуру
docker-compose up
```

### 3. Проверка работоспособности

```bash
# Health check db_connector
curl http://localhost:8001/health

# Health check csv_loader
curl http://localhost:8002/health

# Проверка MCPO
curl http://localhost:8100/health
```
