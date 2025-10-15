#!/bin/bash
# Интерактивный скрипт первого запуска проекта

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   OpenWebUI MCP Server - Первый запуск                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker Desktop."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose не установлен."
    exit 1
fi

echo "✅ Docker найден"
echo ""

# Проверка существования .env файла
if [ -f ".env" ]; then
    echo "⚠️  Файл .env уже существует."
    read -p "   Перезаписать? (y/N): " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo "   Пропускаем создание .env"
        use_existing_env=true
    fi
fi

# Создание .env если нужно
if [ "$use_existing_env" != "true" ]; then
    echo ""
    echo "📝 Настройка окружения..."
    echo ""
    
    # Выбор LLM модели
    echo "Выберите LLM модель для Ollama:"
    echo ""
    echo "  1) qwen2.5:14b-instruct    [Рекомендуется, ~8GB VRAM, лучший русский]"
    echo "  2) qwen2.5:7b-instruct     [Легкая, ~4GB VRAM, быстрая]"
    echo "  3) mistral-nemo:12b        [Средняя, ~7GB VRAM, хороший баланс]"
    echo "  4) llama3.2:3b             [Минимальная, ~2GB VRAM]"
    echo "  5) Ввести свою модель"
    echo ""
    read -p "Ваш выбор (1-5) [1]: " model_choice
    model_choice=${model_choice:-1}
    
    case $model_choice in
        1)
            OLLAMA_MODEL="qwen2.5:14b-instruct"
            ;;
        2)
            OLLAMA_MODEL="qwen2.5:7b-instruct"
            ;;
        3)
            OLLAMA_MODEL="mistral-nemo:12b"
            ;;
        4)
            OLLAMA_MODEL="llama3.2:3b"
            ;;
        5)
            read -p "Введите название модели (например, llama3.1:8b): " custom_model
            OLLAMA_MODEL="$custom_model"
            ;;
        *)
            echo "⚠️  Неверный выбор, используется по умолчанию: qwen2.5:14b-instruct"
            OLLAMA_MODEL="qwen2.5:14b-instruct"
            ;;
    esac
    
    echo ""
    echo "✓ Выбрана модель: $OLLAMA_MODEL"
    echo ""
    
    # Создание .env файла
    cat > .env << ENVEOF
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgress
POSTGRES_DB=ai_assistant

# Database URL for MCP servers
DATABASE_URL=postgresql://postgres:postgress@postgres:5432/ai_assistant

# Ollama Configuration
OLLAMA_MODEL=$OLLAMA_MODEL

# Optional: Uncomment to change default ports
# OPENWEBUI_PORT=3000
# MCPO_PORT=8100
# OLLAMA_PORT=11434
# POSTGRES_PORT=5432
ENVEOF
    
    echo "✅ Файл .env создан"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📦 Загрузка модели в Ollama..."
echo "════════════════════════════════════════════════════════════"
echo ""

# Получаем название модели из .env
if [ -f ".env" ]; then
    source .env
fi

OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:14b-instruct}

echo "Модель: $OLLAMA_MODEL"
echo ""

# Проверяем запущен ли контейнер ollama
if docker ps --format '{{.Names}}' | grep -q "^ollama$"; then
    echo "✓ Контейнер Ollama уже запущен"
else
    echo "🚀 Запускаем Ollama..."
    docker-compose up -d ollama
    echo "⏳ Ждем готовности Ollama..."
    sleep 10
fi

# Загружаем модель
echo "📥 Загружаем модель $OLLAMA_MODEL (это может занять несколько минут)..."
docker exec ollama ollama pull "$OLLAMA_MODEL"

echo ""
echo "✅ Модель загружена!"
echo ""

echo "════════════════════════════════════════════════════════════"
echo "🚀 Запуск всех сервисов..."
echo "════════════════════════════════════════════════════════════"
echo ""

# Собираем образы
echo "🔨 Сборка образов MCP серверов..."
docker-compose build

# Запускаем все сервисы
echo "🚀 Запуск сервисов..."
docker-compose up -d

echo ""
echo "⏳ Ожидание готовности сервисов (30 сек)..."
sleep 30

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ Проект запущен!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📍 Доступные сервисы:"
echo ""
echo "   • OpenWebUI:  http://localhost:3000"
echo "   • MCPO API:   http://localhost:8100"
echo "   • Ollama API: http://localhost:11434"
echo "   • PostgreSQL: localhost:5432"
echo ""
echo "📖 Полезные команды:"
echo ""
echo "   Просмотр логов:        docker-compose logs -f"
echo "   Остановить проект:     docker-compose down"
echo "   Перезапустить:         docker-compose restart"
echo "   Статус контейнеров:    docker-compose ps"
echo ""
echo "🎉 Готово! Откройте http://localhost:3000 в браузере"
echo ""
