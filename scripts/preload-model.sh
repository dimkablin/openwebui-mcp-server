#!/bin/bash
# Скрипт для предзагрузки модели Ollama при старте контейнера
# Использует OLLAMA_KEEP_ALIVE=-1 для постоянного хранения модели в памяти

set -e

echo "🚀 Starting Ollama service..."
echo "   OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE:--1} (модель останется в памяти)"

# Запускаем Ollama в фоне
ollama serve &
OLLAMA_PID=$!

# Загружаем модель в память
MODEL_NAME="${OLLAMA_MODEL:-qwen2.5:14b-instruct}"
echo ""
echo "📦 Triggering model preload: $MODEL_NAME"

# Проверяем есть ли модель
if ! ollama list | grep -q "$MODEL_NAME"; then
    echo "⚠️  Model $MODEL_NAME not found in local storage"
    echo "   Skipping preload. Model will be loaded on first request."
    echo "   To download: docker exec ollama ollama pull $MODEL_NAME"
else
    echo "   ✓ Model found in local storage"
    echo "   🚀 Sending preload request (loading in background)..."

    # Отправляем запрос в фоне - модель начнёт загружаться
    curl -s http://localhost:11434/api/generate -d "{
      \"model\": \"$MODEL_NAME\",
      \"prompt\": \"\",
      \"stream\": false,
      \"options\": {
        \"num_predict\": 1
      }
    }" > /dev/null 2>&1 &

    echo "   ✅ Preload request sent! Model is loading in background."
    echo "   💡 First user request may still see 'loading tensors' but will be faster."
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎉 Ollama service is ready!"
echo "   • Model: $MODEL_NAME"
echo "   • Keep alive: ${OLLAMA_KEEP_ALIVE:--1} (постоянно в памяти)"
echo "   • API: http://localhost:11434"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Keep the container running by waiting for the Ollama process
wait $OLLAMA_PID
