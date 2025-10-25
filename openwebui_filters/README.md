# OpenWebUI Advanced Memory RAG Filter (LiteLLM + BGE-M3)

Интеллектуальный фильтр с **векторным поиском воспоминаний** + **RAG по истории чата** для работы с большими диалогами.

## 🎯 Возможности

### 1. **Долговременная память (Long-term Memory)**

- ✅ Векторный поиск релевантных воспоминаний через LiteLLM Embeddings (BGE-M3)
- ✅ Автоматическое сохранение знаний по команде пользователя
- ✅ Инъекция персональных воспоминаний в контекст LLM

### 2. **RAG по истории чата (Chat History RAG)** 🆕

- ✅ Автоматическая индексация всех сообщений в диалоге
- ✅ Векторный поиск релевантных старых сообщений через BGE-M3
- ✅ Решает проблему потери контекста в длинных диалогах

**Проблема:** LLM забывает что было 10+ сообщений назад
**Решение:** Фильтр находит и подтягивает релевантный старый контекст

## 📦 Установка

### Шаг 1: Разверните LiteLLM локально (рекомендуется)

**Вариант A: Локальный LiteLLM через Docker** (рекомендуется)

1. Загрузите модель BGE-M3:
```bash
docker exec ollama ollama pull bge-m3
```

2. Запустите LiteLLM сервис:
```bash
docker compose up -d litellm
```

3. Проверьте работу:
```bash
curl http://localhost:4000/health
curl http://localhost:4000/v1/models
```

📖 **Подробная инструкция:** [SETUP_LITELLM.md](SETUP_LITELLM.md)

---

**Вариант B: Удаленный LiteLLM сервер**

Если у вас уже есть LiteLLM на сервере:

```bash
# Проверьте доступность
curl https://your-litellm-server.com/v1/models \
  -H "Authorization: Bearer your-api-key"
```

### Шаг 2: Добавьте фильтр в OpenWebUI

1. Откройте OpenWebUI: http://localhost:3000
2. Перейдите в **Settings** (⚙️) → **Functions**
3. Нажмите **"+ Create New Function"**
4. Скопируйте содержимое файла `memory_rag_filter.py`
5. Вставьте в редактор и сохраните

### Шаг 3: Настройте фильтр

В настройках фильтра укажите:

**Для локального LiteLLM:**
```yaml
litellm_base_url: http://litellm:4000
litellm_api_key: sk-litellm-master-key
embedding_model: bge-m3
```

**Для удаленного LiteLLM:**
```yaml
litellm_base_url: https://your-server.com
litellm_api_key: your-api-key
embedding_model: bge-m3
```

**Опциональные параметры:**
- `enable_chat_history_rag` = `true` - RAG по истории чата
- `chat_history_similarity_threshold` = `0.5` - порог релевантности (0-1)
- `vector_similarity_threshold` = `0.65` - порог для долговременной памяти

**💡 Архитектура:**
- **Эмбеддинги:** LiteLLM → Ollama BGE-M3 (1024 dimensions, multilingual)
- **Долговременная память:** OpenWebUI Memories API (PostgreSQL)
- **Хранение истории:** In-memory (только текущая сессия)

## 🚀 Использование

### A) Добавление знаний в долговременную память

Используйте команды в чате:

**Русский:**

```text
запомни что я люблю пиццу
сохрани знание: мой день рождения 15 марта
добавь в память: я работаю Python-разработчиком
```

**English:**

```text
remember that I prefer dark mode
save to memory: my favorite color is blue
```

Фильтр автоматически распознает команду, извлечёт знание и сохранит в OpenWebUI Memories.

### B) Автоматический RAG по истории чата

Фильтр работает автоматически - просто ведите диалог:

**Пример:**

```text
Сообщение 1: "Проанализируй этот CSV с продажами"
Сообщение 2: "Electronics принесла $45K"
...
Сообщение 15: "Сколько было у Electronics?"
```

→ Фильтр найдёт сообщение #2 и подтянет в контекст
→ LLM ответит точно: "$45,000"

Подробнее: см. [CHAT_HISTORY_RAG.md](CHAT_HISTORY_RAG.md)

## ⚙️ Основные параметры

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `litellm_base_url` | `https://litellm.scibox.inno.tech` | URL LiteLLM API сервера |
| `litellm_api_key` | `""` | API ключ для LiteLLM |
| `embedding_model` | `bge-m3` | Модель для эмбеддингов |
| `enable_chat_history_rag` | `true` | RAG по истории чата |
| `chat_history_similarity_threshold` | `0.7` | Порог релевантности для истории (0-1) |
| `max_chat_history_results` | `3` | Сколько старых сообщений подтягивать |
| `vector_similarity_threshold` | `0.65` | Порог для долговременной памяти (0-1) |
| `max_memories_to_inject` | `5` | Максимум воспоминаний в контексте |

## 📚 Дополнительная документация

- **[CHAT_HISTORY_RAG.md](CHAT_HISTORY_RAG.md)** - Подробное описание RAG по истории чата
- **[README_MEMORY_FILTER.md](README_MEMORY_FILTER.md)** - Полная документация по фильтру
- **[DEMO_RESULTS.md](DEMO_RESULTS.md)** - Результаты тестирования

## 🔧 Troubleshooting

**Проблема:** LiteLLM API не доступен
**Решение:**
- Проверьте доступность: `curl https://your-litellm-server.com/v1/models -H "x-litellm-api-key: YOUR_KEY"`
- Убедитесь что `litellm_base_url` указан правильно
- Проверьте что API ключ (`litellm_api_key`) корректный

**Проблема:** Модель BGE-M3 не найдена
**Решение:**
- Убедитесь что модель `bge-m3` доступна на вашем LiteLLM сервере
- Проверьте список моделей: `GET /v1/models`

**Проблема:** Не находит релевантные сообщения
**Решение:** Уменьшите `chat_history_similarity_threshold` с 0.7 до 0.6

## ✅ Тестирование

Запустите тесты:

```bash
cd openwebui_filters
python test_chat_history_rag.py
```

Все 5 тестов должны пройти успешно.

---

**Лицензия:** MIT
**Автор:** Разработано для OpenWebUI
