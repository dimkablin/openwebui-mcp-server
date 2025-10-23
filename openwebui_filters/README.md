# OpenWebUI Memory RAG Filter

Упрощённый фильтр для **векторного поиска и подстановки воспоминаний** в контекст LLM.

## 🎯 Что делает фильтр

**ТОЛЬКО RAG (Retrieval-Augmented Generation):**
- ✅ Ищет релевантные воспоминания через векторный поиск
- ✅ Добавляет их в контекст LLM автоматически
- ✅ Показывает использованные воспоминания в ответе
- ❌ **НЕ** сохраняет новые воспоминания автоматически
- ❌ **НЕ** использует LLM для оценки релевантности (только векторы)
- ❌ **НЕ** делает кластеризацию/суммаризацию

## 📦 Установка

### Шаг 1: Установите зависимости

В контейнере OpenWebUI или локально:

```bash
pip install sentence-transformers numpy
```

**Что устанавливается:**
- `sentence-transformers` - модель эмбеддингов (~100MB)
- `numpy` - математические операции с векторами

### Шаг 2: Добавьте фильтр в OpenWebUI

#### Вариант A: Через UI (рекомендуется)

1. Откройте OpenWebUI: http://localhost:3000
2. Перейдите в **Settings** (⚙️) → **Functions**
3. Нажмите **"+ Add Function"**
4. Скопируйте содержимое файла `memory_rag_simple.py`
5. Вставьте в редактор
6. Нажмите **Save**

#### Вариант B: Через файловую систему (для разработки)

```bash
# Скопируйте фильтр в директорию OpenWebUI
docker cp memory_rag_simple.py openwebui:/app/backend/open_webui/functions/

# Перезапустите OpenWebUI
docker restart openwebui
```

## ⚙️ Настройка

После добавления фильтра откройте его настройки в OpenWebUI:

### Основные параметры (Valves)

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `vector_similarity_threshold` | `0.65` | Порог схожести (0-1). Меньше = больше воспоминаний |
| `max_memories_to_inject` | `5` | Максимум воспоминаний в контексте |
| `show_injected_memories` | `true` | Показывать список использованных воспоминаний |
| `memory_display_format` | `bullet` | Формат: `bullet`, `numbered`, `paragraph` |
| `enable_filter` | `true` | Включить/выключить фильтр |

### Настройка порога similarity

**Как работает порог:**
- `0.9-1.0` - Очень строго (только почти идентичные воспоминания)
- `0.7-0.8` - Сбалансированно (рекомендуется)
- `0.5-0.6` - Свободно (много воспоминаний, могут быть нерелевантные)

**Пример:**

Запрос: *"Какая погода в моём городе?"*

| Порог | Результат |
|-------|-----------|
| `0.9` | Только "User lives in Moscow" (similarity: 0.92) |
| `0.7` | + "User likes cold weather" (similarity: 0.74) |
| `0.5` | + "User's friend lives in London" (similarity: 0.58) |

## 💾 Добавление воспоминаний

Поскольку фильтр **не сохраняет** воспоминания автоматически, добавляйте их вручную:

### Способ 1: Через UI OpenWebUI

1. Откройте **Settings** → **Memories**
2. Нажмите **"+ Add Memory"**
3. Введите текст воспоминания
4. Сохраните

**Примеры воспоминаний:**
```
User lives in Moscow, Russia
User works as a Python developer at Yandex
User prefers dark roast coffee
User's cat is named Luna
User is learning machine learning
```

### Способ 2: Через API

```bash
curl -X POST http://localhost:3000/api/v1/memories \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User lives in Moscow",
    "user_id": "user_123"
  }'
```

### Способ 3: Через Python скрипт

```python
from open_webui.routers.memories import add_memory, AddMemoryForm

# Добавить воспоминание
add_memory(AddMemoryForm(
    user_id="user_123",
    content="User lives in Moscow"
))
```

## 🚀 Использование

### Пример диалога

**Шаг 1:** Добавьте воспоминания вручную:
```
- User lives in Moscow
- User works as Python developer
- User loves sushi
```

**Шаг 2:** Задайте вопрос в чате:
```
User: Какие суши-бары есть рядом со мной?
```

**Что происходит:**
1. Фильтр генерирует эмбеддинг вопроса
2. Сравнивает с эмбеддингами воспоминаний
3. Находит релевантные:
   - "User lives in Moscow" (similarity: 0.89)
   - "User loves sushi" (similarity: 0.94)
4. Добавляет в системный промпт:
   ```
   ===== RELEVANT USER MEMORIES =====
   - User lives in Moscow
   - User loves sushi
   ==================================
   ```
5. LLM видит контекст и отвечает:
   ```
   Рядом с вами в Москве есть несколько отличных суши-баров:
   1. Тануки на Тверской...
   ```

### Проверка работы

В конце ответа вы увидите:

```
---
📚 Использованные воспоминания:
- User lives in Moscow
- User loves sushi
```

Это подтверждает, что фильтр работает!

## 🔧 Отладка

### Проблема: "No relevant memories found"

**Причины:**
1. Нет воспоминаний в БД для пользователя
2. Порог `vector_similarity_threshold` слишком высокий
3. Воспоминания не релевантны запросу

**Решение:**
```python
# Проверьте логи OpenWebUI
docker logs openwebui | grep "memory_rag"

# Понизьте порог
vector_similarity_threshold: 0.5  # Было 0.65
```

### Проблема: "Embedding model not available"

**Причина:** Не установлен `sentence-transformers`

**Решение:**
```bash
# В контейнере OpenWebUI
docker exec -it openwebui pip install sentence-transformers

# Перезапустите контейнер
docker restart openwebui
```

### Проблема: Слишком много нерелевантных воспоминаний

**Решение:**
```python
# Увеличьте порог
vector_similarity_threshold: 0.75  # Было 0.65

# Уменьшите количество
max_memories_to_inject: 3  # Было 5
```

## 📊 Производительность

### Скорость

- **Векторный поиск:** ~10-50ms для 100 воспоминаний
- **Генерация эмбеддинга:** ~50-100ms
- **Общая задержка:** ~100-200ms

### Использование памяти

- **Модель эмбеддингов:** ~80MB RAM
- **Кэш эмбеддингов:** ~1KB на воспоминание
- **Для 1000 воспоминаний:** ~81MB RAM

## 🆚 Сравнение с полной версией Adaptive Memory

| Функция | RAG Simple | Adaptive Memory v3.0 |
|---------|------------|---------------------|
| **Векторный поиск** | ✅ | ✅ |
| **Инъекция в контекст** | ✅ | ✅ |
| **Автосохранение** | ❌ | ✅ |
| **LLM оценка релевантности** | ❌ | ✅ (опционально) |
| **Дедупликация** | ❌ | ✅ |
| **Кластеризация** | ❌ | ✅ |
| **Memory Banks** | ❌ (упрощённо) | ✅ |
| **Размер кода** | ~300 строк | ~2000+ строк |
| **Сложность** | Простая | Высокая |

## 🔐 Memory Banks (опционально)

Если вы используете теги в воспоминаниях, можно фильтровать по банкам:

```python
# В настройках фильтра
use_memory_banks: true
active_memory_bank: "Personal"  # или "Work" или "General"
```

**Формат воспоминаний с банками:**
```
[Bank: Personal] User lives in Moscow
[Bank: Work] User is a Python developer at Yandex
[Bank: General] User is interested in astronomy
```

Тогда при `active_memory_bank: "Work"` будут использоваться только рабочие воспоминания.

## 📝 Лицензия

MIT

---

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker logs openwebui | grep "memory_rag"`
2. Убедитесь что зависимости установлены
3. Проверьте что воспоминания добавлены в БД
4. Откройте issue в репозитории

---

**Автор:** DVZolotarev
**Дата:** 2025-10-20
