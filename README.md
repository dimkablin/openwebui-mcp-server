# OpenWebUI MCP Server

> Система MCP серверов для журналирования, аналитики настроения и автоматических напоминаний, интегрированная с OpenWebUI и Ollama

## Описание

Это набор из трёх специализированных MCP (Model Context Protocol) серверов, предназначенных для создания интеллектуального ассистента с функциями:
- 📝 Ведения личного дневника с анализом эмоционального состояния
- 📊 Визуализации и аналитики данных по настроению
- ⏰ Автоматических напоминаний и регулярных проверок состояния

Все серверы работают через единую точку входа (MCPO) и доступны из OpenWebUI через Ollama.

## Архитектура

```
┌───────────────────────────────────────────────────┐
│              OpenWebUI (порт 3000)                │
│  ┌────────────────┐    ┌───────────────────────┐  │
│  │  Пользователь  │    │    Ollama (11434)     │  │
│  └────────────────┘    └───────────────────────┘  │
└────────────────┬──────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │  MCPO (8100)  │  ← Прокси для всех MCP серверов
         └───────┬───────┘
                 │
     ┌───────────┼───────────┐
     ▼           ▼           ▼
┌─────────┐ ┌──────────┐ ┌───────────┐
│ journal │ │analytics │ │ scheduler │
│  (8003) │ │  (8004)  │ │  (8005)   │
└─────────┘ └──────────┘ └───────────┘
     └───────────┬───────────┘
                 ▼
         ┌──────────────┐
         │  PostgreSQL  │  ← Единая БД для всех серверов
         │  (порт 5432) │
         └──────────────┘
```

## MCP Серверы

### 🧠 journal_server (порт 8003)
**Дневник и контекст** - хранение диалогов с автоматической оценкой настроения

**Функции:**
- `create_entry(text, mood?, tags?)` - создать запись в дневнике
- `extract_assessment(text)` - извлечь метрики настроения (valence, anxiety, energy)
- `save_assessment(entry_id, assessment)` - сохранить оценку в БД
- `get_context(limit=10)` - получить последние записи для контекста

**Бэкенд:** PostgreSQL

---

### 📊 analytics_server (порт 8004)
**Аналитика и графики** - агрегация и визуализация данных

**Функции:**
- `trends(metric, window)` - динамика показателя за период (day/week/month)
- `weekly_report()` - краткий отчёт по всем метрикам за неделю
- `charts(metrics, from_date, to_date)` - генерация графиков
- `export_csv(from_date, to_date)` - выгрузка данных в CSV

**Бэкенд:** PostgreSQL/TimescaleDB + Matplotlib/Plotly

---

### ⏰ scheduler_server (порт 8005)
**Напоминания и ритуалы** - автоматические вопросы и задания

**Функции:**
- `add_rule(cron, prompt, description?)` - добавить правило с расписанием
- `list_rules()` - получить список всех правил
- `remove_rule(rule_id)` - удалить правило по ID
- `trigger_now(rule_id)` - запустить правило немедленно (для тестирования)

**Бэкенд:** PostgreSQL + APScheduler

---

## Технологический стек

- **Python 3.11+** с async/await
- **FastMCP** - фреймворк для создания MCP серверов
- **PostgreSQL 16** - основная БД для хранения данных
- **OpenWebUI** - веб-интерфейс для взаимодействия
- **Ollama** - локальное развёртывание LLM моделей
- **MCPO** - прокси для агрегации MCP серверов
- **Docker & Docker Compose** - контейнеризация

### Зависимости по серверам:
- **journal**: asyncpg
- **analytics**: asyncpg, pandas, matplotlib, plotly
- **scheduler**: asyncpg, apscheduler

---

## Быстрый запуск

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- [uv](https://github.com/astral-sh/uv) - современный пакетный менеджер для Python

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd openwebui-mcp-server
```

### 2. Установка зависимостей (опционально, для разработки)

```bash
# Установить все зависимости
uv sync --all-extras

# Или только для конкретных серверов
uv sync --extra journal_server
uv sync --extra analytics_server
uv sync --extra scheduler_server
```

### 3. Настройка окружения

Создайте файл `.env` в корне проекта:

```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgress
POSTGRES_DB=ai_assistant

# Database URLs для каждого сервера
DATABASE_URL=postgresql://postgres:postgress@postgres:5432/ai_assistant
```

### 4. Запуск через Docker Compose

```bash
# Собрать образы
docker-compose build

# Запустить всю инфраструктуру
docker-compose up -d

# Проверить статус контейнеров
docker-compose ps
```

### 5. Проверка работоспособности

```bash
# Health checks для MCP серверов
curl http://localhost:8003/health  # journal
curl http://localhost:8004/health  # analytics
curl http://localhost:8005/health  # scheduler

# Проверка MCPO
curl http://localhost:8100/health

# Проверка OpenWebUI
curl http://localhost:3000
```

### 6. Доступ к сервисам

- **OpenWebUI**: http://localhost:3000
- **MCPO**: http://localhost:8100
- **Ollama**: http://localhost:11434
- **PostgreSQL**: http://localhost:5432

---

## Структура проекта

```
openwebui-mcp-server/
├── app/
│   ├── journal_server/       # Сервер дневника
│   │   ├── main.py          # Точка входа
│   │   ├── tools/           # Реализация MCP tools
│   │   ├── resources/       # MCP resources
│   │   └── prompts/         # MCP prompts
│   ├── analytics_server/    # Сервер аналитики
│   │   └── ...
│   ├── scheduler_server/    # Сервер планировщика
│   │   └── ...
│   ├── config.py           # Конфигурация
│   ├── healthcheck.py      # Health check endpoint
│   └── lifespan.py         # Lifecycle management
├── docker-compose.yml       # Orchestration
├── Dockerfile              # Образ для MCP серверов
├── mcpo.config.json        # Конфигурация MCPO
├── pyproject.toml          # Зависимости проекта
└── README.md              # Этот файл
```

---

## Разработка

### Локальный запуск отдельного сервера

```bash
# Journal server
uv run -m app.journal_server.main --host 0.0.0.0 --port 8003

# Analytics server
uv run -m app.analytics_server.main --host 0.0.0.0 --port 8004

# Scheduler server
uv run -m app.scheduler_server.main --host 0.0.0.0 --port 8005
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f mcp-server-journal
docker-compose logs -f openwebui
```

### Остановка и удаление

```bash
# Остановить все контейнеры
docker-compose down

# Удалить volumes (ВНИМАНИЕ: удалит все данные!)
docker-compose down -v
```

---

## Roadmap

- [ ] Реализация базовых функций journal_server
- [ ] Создание схемы БД для всех серверов
- [ ] Реализация analytics_server с визуализацией
- [ ] Интеграция scheduler_server с APScheduler
- [ ] Добавление тестов
- [ ] CI/CD pipeline
- [ ] Документация API

---

## Лицензия

MIT

---

## Контакты

DVZolotarev - [@dimkablin](https://t.me/dimkablin)
