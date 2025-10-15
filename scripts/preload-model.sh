#!/bin/bash
# Скрипт для предзагрузки модели Ollama при старте контейнера

set -e

echo "🚀 Starting Ollama service..."
# Запускаем Ollama в фоне
ollama serve &

# Ждем пока Ollama запустится
echo "⏳ Waiting for Ollama to be ready..."
max_attempts=30
attempt=0
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
        echo "❌ Failed to start Ollama after $max_attempts attempts"
        exit 1
    fi
    echo "   Attempt $attempt/$max_attempts..."
    sleep 2
done

echo "✅ Ollama is ready!"

# Загружаем модель в память
MODEL_NAME="${OLLAMA_MODEL:-qwen2.5:14b-instruct}"
echo "📦 Preloading model: $MODEL_NAME"

# Проверяем есть ли модель
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "⚠️  Model $MODEL_NAME not found. Please pull it first with: ollama pull $MODEL_NAME"
else
    # Делаем запрос к модели, чтобы она загрузилась в память
    echo "   Loading model into memory..."
    curl -s http://localhost:11434/api/generate -d "{
      \"model\": \"$MODEL_NAME\",
      \"prompt\": \"Hi\",
      \"stream\": false,
      \"keep_alive\": -1
    }" > /dev/null && echo "✅ Model $MODEL_NAME loaded into memory!"
fi

# Keep the container running
echo "🎉 Ready! Keeping Ollama service alive..."
wait
