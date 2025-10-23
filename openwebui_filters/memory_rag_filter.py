"""
Advanced Memory RAG Filter for OpenWebUI using Ollama Embeddings
Долговременная память + RAG по истории чата для работы с большими диалогами

Возможности:
1. ДОЛГОВРЕМЕННАЯ ПАМЯТЬ (Long-term Memory):
   - Векторный поиск релевантных воспоминаний через Ollama Embeddings API
   - Автоматическое сохранение знаний по запросу пользователя
   - Инъекция персональных воспоминаний в контекст LLM

2. RAG ПО ИСТОРИИ ЧАТА (Chat History RAG):
   - Автоматическая индексация всех сообщений в диалоге
   - Векторный поиск релевантных старых сообщений
   - Суммаризация длинных сообщений для экономии контекста
   - Подтягивание забытого контекста при длинных диалогах

3. ИНТЕГРАЦИЯ:
   - Работает с локальным Ollama (без дополнительных зависимостей)
   - Минимум установки - только aiohttp
   - Хранение в памяти (только текущая сессия)

Использование:
1. Убедитесь что Ollama запущен и доступен
2. Загрузите модели:
   - ollama pull nomic-embed-text  (для embeddings)
   - ollama pull llama3.2:latest   (для суммаризации)
3. Добавьте фильтр в OpenWebUI через Settings → Functions

Примеры использования:

A) Добавление знаний (long-term memory):
   - "запомни что я люблю пиццу с ананасами"
   - "сохрани знание: мой день рождения 15 марта"
   - "добавь в память: я работаю Python-разработчиком в Google"
   - "remember that I prefer dark mode"
   - "save to memory: my favorite color is blue"

B) Автоматический RAG по истории чата:
   Сценарий: Вы работаете с данными CSV, обсуждаете анализ 10 сообщений,
   затем спрашиваете "а что было с колонкой sales?"
   → Фильтр автоматически находит релевантные сообщения из начала диалога
   → LLM получает контекст и отвечает точно

Как это решает проблему потери контекста:
- LLM часто забывает что было 10+ сообщений назад
- Фильтр индексирует все сообщения с векторами
- При новом запросе ищет семантически похожие старые сообщения
- Добавляет их как дополнительный контекст
- LLM "вспоминает" что обсуждалось раньше
"""

import logging
import aiohttp
from typing import Any, Awaitable, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

# Импорты для работы с памятью OpenWebUI
try:
    from open_webui.routers.memories import query_memory, QueryMemoryForm
    from open_webui.models.memories import Memories, MemoryModel
except ImportError:
    # Fallback для тестирования вне OpenWebUI
    query_memory = None
    QueryMemoryForm = None
    Memories = None
    MemoryModel = None

# Настройка логирования
logger = logging.getLogger("openwebui.filters.memory_rag_ollama")


class Filter:
    """RAG-only фильтр для поиска и инъекции воспоминаний через Ollama"""

    class Valves(BaseModel):
        """Настройки фильтра"""

        # === Ollama Configuration ===
        ollama_base_url: str = Field(
            default="http://host.docker.internal:11434",
            description="URL Ollama API (внутри Docker используйте host.docker.internal)",
        )

        embedding_model: str = Field(
            default="nomic-embed-text",
            description="Модель для генерации эмбеддингов (nomic-embed-text, mxbai-embed-large, etc.)",
        )

        # === Векторный поиск ===
        vector_similarity_threshold: float = Field(
            default=0.65,
            description="Минимальное косинусное сходство для релевантности (0-1). Ниже = больше воспоминаний.",
        )

        max_memories_to_inject: int = Field(
            default=5,
            description="Максимальное количество воспоминаний для добавления в контекст",
        )

        # === Memory Banks (опционально) ===
        use_memory_banks: bool = Field(
            default=False,
            description="Фильтровать воспоминания по банкам (Personal/Work/General)",
        )

        active_memory_bank: str = Field(
            default="Personal",
            description="Активный банк памяти (если use_memory_banks=True)",
        )

        # === Отображение ===
        show_injected_memories: bool = Field(
            default=True,
            description="Показывать список использованных воспоминаний в ответе",
        )

        memory_display_format: str = Field(
            default="bullet",
            description="Формат отображения: 'bullet', 'numbered', 'paragraph'",
        )

        max_memory_display_length: int = Field(
            default=200,
            description="Максимальная длина каждого воспоминания для отображения (символов)",
        )

        # === Продвинутые настройки ===
        enable_filter: bool = Field(
            default=True, description="Включить/выключить фильтр памяти"
        )

        cache_embeddings: bool = Field(
            default=True, description="Кэшировать эмбеддинги воспоминаний для ускорения"
        )

        request_timeout: int = Field(
            default=30, description="Таймаут запросов к Ollama (секунды)"
        )

        # === Векторное хранилище истории чата ===
        enable_chat_history_rag: bool = Field(
            default=True,
            description="Включить RAG по истории чата (находит релевантные старые сообщения)"
        )

        chat_history_similarity_threshold: float = Field(
            default=0.7,
            description="Порог сходства для поиска в истории чата (0-1)"
        )

        max_chat_history_results: int = Field(
            default=3,
            description="Максимальное количество старых сообщений для подтягивания"
        )

        chat_history_index_window: int = Field(
            default=50,
            description="Индексировать последние N сообщений (0 = все сообщения)"
        )

        summarize_long_messages: bool = Field(
            default=True,
            description="Суммаризировать длинные сообщения для экономии контекста"
        )

        summarization_threshold: int = Field(
            default=500,
            description="Длина сообщения (символов) для суммаризации"
        )

        summarization_model: str = Field(
            default="llama3.2:latest",
            description="Модель Ollama для суммаризации текста"
        )

    class UserValves(BaseModel):
        """Пользовательские настройки"""

        show_status: bool = Field(
            default=True, description="Показывать статус поиска памяти"
        )

    def __init__(self):
        """Инициализация фильтра"""
        self.valves = self.Valves()

        # Кэш эмбеддингов: {memory_id: List[float]}
        self._memory_embeddings_cache: Dict[str, List[float]] = {}

        # Последние использованные воспоминания (для отображения)
        self._last_injected_memories: List[str] = []

        # HTTP сессия для Ollama API
        self._session: Optional[aiohttp.ClientSession] = None

        # === Векторное хранилище истории чата ===
        # Структура: {
        #   "msg_hash": {
        #       "index": int,           # Позиция в массиве messages
        #       "role": str,            # user/assistant
        #       "content": str,         # Полный текст (для восстановления)
        #       "summary": str,         # Краткое содержание (если суммаризировано)
        #       "embedding": List[float], # Вектор
        #       "timestamp": float,     # Время индексации
        #   }
        # }
        self._chat_history_index: Dict[str, Dict[str, Any]] = {}

        # Кэш суммаризаций: {msg_hash: summary}
        self._summarization_cache: Dict[str, str] = {}

        logger.info(
            f"✅ Ollama Memory RAG Filter initialized (model: {self.valves.embedding_model})"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать aiohttp сессию"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Генерация эмбеддинга через Ollama Embeddings API

        Args:
            text: Текст для векторизации

        Returns:
            List[float]: Вектор эмбеддинга или None при ошибке
        """
        try:
            session = await self._get_session()
            url = f"{self.valves.ollama_base_url}/api/embeddings"

            payload = {"model": self.valves.embedding_model, "prompt": text}

            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.valves.request_timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama API error {response.status}: {error_text}")
                    return None

                data = await response.json()
                embedding = data.get("embedding")

                if not embedding:
                    logger.error(f"No embedding in Ollama response: {data}")
                    return None

                return embedding

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error calling Ollama: {e}")
            return None
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None

    async def _summarize_text(self, text: str, max_length: int = 200) -> Optional[str]:
        """
        Суммаризация текста через Ollama Chat API

        Args:
            text: Текст для суммаризации
            max_length: Максимальная длина саммари (символов)

        Returns:
            str: Краткое содержание или None при ошибке
        """
        # Проверяем кэш
        text_hash = str(hash(text))
        if text_hash in self._summarization_cache:
            return self._summarization_cache[text_hash]

        try:
            session = await self._get_session()
            url = f"{self.valves.ollama_base_url}/api/generate"

            # Промпт для суммаризации
            prompt = f"""Summarize the following message in 1-2 concise sentences (max {max_length} chars). Focus on key information and context:

{text[:2000]}

Summary:"""

            payload = {
                "model": self.valves.summarization_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Низкая температура для более точной суммаризации
                    "num_predict": 100,   # Ограничение длины
                }
            }

            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.valves.request_timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Ollama summarization error {response.status}: {error_text}")
                    return None

                data = await response.json()
                summary = data.get("response", "").strip()

                if not summary:
                    logger.warning("Empty summary from Ollama")
                    # Fallback: берём первые N символов
                    return text[:max_length] + "..." if len(text) > max_length else text

                # Обрезаем если слишком длинный
                if len(summary) > max_length:
                    summary = summary[:max_length] + "..."

                # Кэшируем
                self._summarization_cache[text_hash] = summary

                return summary

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error during summarization: {e}")
            return text[:max_length] + "..." if len(text) > max_length else text
        except Exception as e:
            logger.error(f"Error summarizing text: {e}", exc_info=True)
            return text[:max_length] + "..." if len(text) > max_length else text

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Вычисление косинусного сходства между двумя векторами

        Args:
            vec1, vec2: Векторы для сравнения

        Returns:
            float: Косинусное сходство (0-1)
        """
        if len(vec1) != len(vec2):
            logger.warning(f"Vector dimension mismatch: {len(vec1)} vs {len(vec2)}")
            return 0.0

        # Скалярное произведение
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Нормы векторов
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def inlet(
        self,
        body: Dict[str, Any],
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
        __user__: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Обработка входящего запроса:
        1. Извлекает последнее сообщение пользователя
        2. Ищет релевантные воспоминания через Ollama embeddings
        3. Добавляет их в системный промпт
        """

        # Сброс последних воспоминаний
        self._last_injected_memories = []

        # Проверки
        if not self.valves.enable_filter:
            return body

        # ВАЖНО: Игнорируем если в body указана модель эмбеддингов
        # (OpenWebUI может пытаться вызвать её напрямую для чата)
        if "model" in body and self.valves.embedding_model in body["model"]:
            logger.debug(
                f"Skipping - embedding model {body['model']} should not be used for chat"
            )
            return body

        if not __user__:
            logger.debug("No user context provided, skipping memory retrieval")
            return body

        if "messages" not in body or not body["messages"]:
            return body

        try:
            # Получаем последнее сообщение пользователя
            user_messages = [m for m in body["messages"] if m.get("role") == "user"]
            if not user_messages:
                return body

            last_user_message = user_messages[-1].get("content", "")
            if not last_user_message.strip():
                return body

            user_id = __user__.get("id")
            if not user_id:
                logger.warning("User ID not found in __user__")
                return body

            # === ПРОВЕРКА: Это запрос на сохранение знания? ===
            memory_to_save = self._is_memory_save_request(last_user_message)

            if memory_to_save:
                logger.info(f"Detected memory save request: {memory_to_save[:50]}...")

                # Сохраняем знание
                success = await self.add_memory(
                    content=memory_to_save,
                    user_id=user_id,
                    __event_emitter__=__event_emitter__
                )

                if success:
                    # Добавляем подтверждение в ответ системы
                    confirmation_msg = (
                        f"✅ Сохранено в память: {memory_to_save[:100]}"
                        f"{'...' if len(memory_to_save) > 100 else ''}"
                    )

                    # Добавляем системное сообщение с подтверждением
                    body["messages"].append({
                        "role": "system",
                        "content": confirmation_msg
                    })

                # Возвращаем body (можно добавить флаг, что LLM должна ответить подтверждением)
                return body

            # === ИНДЕКСАЦИЯ ИСТОРИИ ЧАТА ===
            # Индексируем историю чата для векторного поиска
            if self.valves.enable_chat_history_rag and len(body["messages"]) > 1:
                await self._index_chat_history(
                    messages=body["messages"][:-1],  # Исключаем последнее сообщение (текущий запрос)
                    __event_emitter__=__event_emitter__
                )

            # === ПОИСК РЕЛЕВАНТНЫХ СТАРЫХ СООБЩЕНИЙ ===
            relevant_history = []
            if self.valves.enable_chat_history_rag:
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "🔍 Searching relevant context from chat history...",
                                "done": False,
                            },
                        }
                    )

                relevant_history = await self._search_chat_history(
                    query_text=last_user_message,
                    exclude_recent=5  # Исключаем последние 5 сообщений (уже в контексте)
                )

            # === ПОИСК РЕЛЕВАНТНЫХ ВОСПОМИНАНИЙ (LONG-TERM MEMORY) ===
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "🔍 Searching relevant memories via Ollama...",
                            "done": False,
                        },
                    }
                )

            relevant_memories = await self._find_relevant_memories(
                query_text=last_user_message, user_id=user_id
            )

            # === ФОРМИРОВАНИЕ И ИНЪЕКЦИЯ КОНТЕКСТА ===

            # Формируем контекст из истории чата
            history_context = ""
            if relevant_history:
                history_context = self._format_chat_history_context(relevant_history)
                logger.info(f"Found {len(relevant_history)} relevant messages from chat history")

            # Формируем контекст из долговременных воспоминаний
            memory_context = ""
            if relevant_memories:
                self._last_injected_memories = relevant_memories
                memory_context = self._format_memory_context(relevant_memories)
                logger.info(f"Found {len(relevant_memories)} relevant memories")

            # Комбинируем оба контекста
            combined_context = ""

            if history_context:
                combined_context += history_context

            if memory_context:
                combined_context += memory_context

            # Если есть что добавить - инжектим
            if combined_context:
                self._inject_into_system_prompt(body, combined_context)
            else:
                logger.debug("No relevant context found (neither history nor memories)")
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "💭 No relevant context found",
                                "done": True,
                            },
                        }
                    )
                return body

            # Эмитим успех
            if __event_emitter__:
                status_parts = []
                if relevant_history:
                    status_parts.append(f"{len(relevant_history)} chat messages")
                if relevant_memories:
                    status_parts.append(f"{len(relevant_memories)} memories")

                status_msg = "✅ Injected: " + ", ".join(status_parts)

                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": status_msg,
                            "done": True,
                        },
                    }
                )

            logger.info(
                f"✅ Injected context: {len(relevant_history)} history messages, "
                f"{len(relevant_memories)} memories"
            )

        except Exception as e:
            logger.error(f"❌ Error in inlet: {e}", exc_info=True)
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"⚠️ Memory retrieval failed: {str(e)}",
                            "done": True,
                        },
                    }
                )

        return body

    async def outlet(
        self,
        body: Dict[str, Any],
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
        __user__: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Обработка исходящего ответа (опционально показываем использованные воспоминания)
        """

        if not self.valves.show_injected_memories or not self._last_injected_memories:
            return body

        try:
            # Формируем сообщение о использованных воспоминаниях
            memory_list = "\n".join(
                [
                    f"- {mem[:self.valves.max_memory_display_length]}{'...' if len(mem) > self.valves.max_memory_display_length else ''}"
                    for mem in self._last_injected_memories
                ]
            )

            context_message = (
                f"\n\n---\n**📚 Использованные воспоминания:**\n{memory_list}"
            )

            # Добавляем в последнее сообщение ассистента
            if "messages" in body and body["messages"]:
                for msg in reversed(body["messages"]):
                    if msg.get("role") == "assistant":
                        msg["content"] = msg.get("content", "") + context_message
                        break

        except Exception as e:
            logger.error(f"Error in outlet: {e}", exc_info=True)

        return body

    # === Приватные методы ===

    def _generate_message_hash(self, role: str, content: str, index: int) -> str:
        """Генерирует уникальный хэш для сообщения"""
        import hashlib
        data = f"{role}:{index}:{content[:100]}"
        return hashlib.md5(data.encode()).hexdigest()

    async def _index_message(
        self,
        role: str,
        content: str,
        index: int,
    ) -> bool:
        """
        Индексирует одно сообщение в векторное хранилище

        Args:
            role: Роль (user/assistant/system)
            content: Содержимое сообщения
            index: Позиция в массиве messages

        Returns:
            bool: True если успешно проиндексировано
        """
        if not content or not content.strip():
            return False

        # Игнорируем системные сообщения
        if role == "system":
            return False

        try:
            msg_hash = self._generate_message_hash(role, content, index)

            # Уже проиндексировано?
            if msg_hash in self._chat_history_index:
                return True

            # Определяем нужна ли суммаризация
            needs_summary = (
                self.valves.summarize_long_messages
                and len(content) > self.valves.summarization_threshold
            )

            # Суммаризируем если нужно
            summary = None
            if needs_summary:
                summary = await self._summarize_text(content, max_length=200)
                if not summary:
                    summary = content[:200] + "..."
            else:
                summary = content

            # Генерируем embedding для саммари (или полного текста)
            embedding = await self._generate_embedding(summary)

            if not embedding:
                logger.warning(f"Failed to generate embedding for message at index {index}")
                return False

            # Сохраняем в индекс
            import time
            self._chat_history_index[msg_hash] = {
                "index": index,
                "role": role,
                "content": content,
                "summary": summary,
                "embedding": embedding,
                "timestamp": time.time(),
            }

            logger.debug(f"Indexed message {index} ({role}): {summary[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error indexing message: {e}", exc_info=True)
            return False

    async def _index_chat_history(
        self,
        messages: List[Dict[str, Any]],
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> int:
        """
        Индексирует историю чата (или её часть)

        Args:
            messages: Массив сообщений из body["messages"]
            __event_emitter__: Эмиттер для статуса

        Returns:
            int: Количество проиндексированных сообщений
        """
        if not self.valves.enable_chat_history_rag:
            return 0

        indexed_count = 0

        # Определяем окно индексации
        window_size = self.valves.chat_history_index_window
        if window_size > 0:
            # Берём только последние N сообщений
            messages_to_index = messages[-window_size:]
            start_index = max(0, len(messages) - window_size)
        else:
            # Индексируем всё
            messages_to_index = messages
            start_index = 0

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"📇 Indexing {len(messages_to_index)} messages...",
                        "done": False,
                    },
                }
            )

        for i, msg in enumerate(messages_to_index):
            role = msg.get("role", "")
            content = msg.get("content", "")
            actual_index = start_index + i

            success = await self._index_message(role, content, actual_index)
            if success:
                indexed_count += 1

        logger.info(f"Indexed {indexed_count}/{len(messages_to_index)} messages from chat history")

        return indexed_count

    def _is_memory_save_request(self, message: str) -> Optional[str]:
        """
        Определяет, является ли сообщение запросом на сохранение знания

        Поддерживаемые форматы:
        - "запомни что я люблю пиццу"
        - "сохрани знание: мой день рождения 15 марта"
        - "добавь в память: я работаю программистом"
        - "remember that I like pizza"
        - "save to memory: my birthday is March 15"

        Returns:
            str: Извлечённое знание для сохранения, или None если это не запрос на сохранение
        """
        import re

        message_lower = message.lower().strip()

        # Паттерны для определения запроса на сохранение (русский и английский)
        patterns = [
            # Русские паттерны (поддержка "сохрани знание:", "запомни что")
            r"(?:запомни|сохрани|добавь в память|добавь в воспоминания|добавь)(?:\s+(?:что|знание|воспоминание))?\s*:?\s*(.+)",
            # Английские паттерны
            r"(?:remember|save to memory|add to memory|save|store|memorize)(?:\s+(?:that|knowledge|memory))?\s*:?\s*(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                # Извлекаем контент (оригинальный регистр)
                start_pos = match.start(1)
                content = message[start_pos:].strip()

                # Убираем возможные кавычки в начале и конце
                content = content.strip('"\'')

                if content:
                    return content

        return None

    async def _search_chat_history(
        self,
        query_text: str,
        exclude_recent: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Векторный поиск по истории чата

        Args:
            query_text: Текст запроса для поиска
            exclude_recent: Исключить последние N сообщений (чтобы не находить текущий контекст)

        Returns:
            List[Dict]: Список релевантных сообщений с метаданными и similarity score
        """
        if not self.valves.enable_chat_history_rag:
            return []

        if not self._chat_history_index:
            logger.debug("Chat history index is empty")
            return []

        try:
            # Генерируем embedding запроса
            query_embedding = await self._generate_embedding(query_text)
            if not query_embedding:
                logger.error("Failed to generate query embedding for history search")
                return []

            # Вычисляем сходство со всеми проиндексированными сообщениями
            similarities = []
            max_index = max((item["index"] for item in self._chat_history_index.values()), default=0)

            for msg_hash, msg_data in self._chat_history_index.items():
                msg_index = msg_data["index"]

                # Исключаем последние N сообщений (текущий контекст)
                if msg_index > max_index - exclude_recent:
                    continue

                msg_embedding = msg_data["embedding"]
                similarity = self._cosine_similarity(query_embedding, msg_embedding)

                if similarity >= self.valves.chat_history_similarity_threshold:
                    similarities.append({
                        "index": msg_index,
                        "role": msg_data["role"],
                        "content": msg_data["content"],
                        "summary": msg_data["summary"],
                        "similarity": similarity,
                        "timestamp": msg_data["timestamp"],
                    })

            # Сортируем по сходству (убывание)
            similarities.sort(key=lambda x: x["similarity"], reverse=True)

            # Берём топ-N
            top_results = similarities[:self.valves.max_chat_history_results]

            logger.debug(
                f"Found {len(top_results)} relevant messages from chat history "
                f"(threshold: {self.valves.chat_history_similarity_threshold})"
            )

            for item in top_results:
                logger.debug(
                    f"  - Index {item['index']} ({item['role']}), "
                    f"Similarity: {item['similarity']:.3f} | {item['summary'][:50]}..."
                )

            return top_results

        except Exception as e:
            logger.error(f"Error searching chat history: {e}", exc_info=True)
            return []

    async def _find_relevant_memories(self, query_text: str, user_id: str) -> List[str]:
        """
        Векторный поиск релевантных воспоминаний через Ollama

        Returns:
            List[str]: Список текстов релевантных воспоминаний
        """

        if not query_memory or not QueryMemoryForm:
            logger.warning("OpenWebUI memory functions not available")
            return []

        try:
            # 1. Получаем все воспоминания пользователя
            query_form = QueryMemoryForm(
                user_id=user_id, content=""  # Пустой запрос = все воспоминания
            )

            all_memories = await query_memory(query_form)

            if not all_memories:
                logger.debug(f"No memories found for user {user_id}")
                return []

            logger.debug(f"Found {len(all_memories)} total memories for user")

            # 2. Фильтрация по Memory Bank (если включено)
            if self.valves.use_memory_banks:
                all_memories = [
                    m
                    for m in all_memories
                    if self._extract_memory_bank(m.get("memory", ""))
                    == self.valves.active_memory_bank
                ]
                logger.debug(
                    f"Filtered to {len(all_memories)} memories in '{self.valves.active_memory_bank}' bank"
                )

            if not all_memories:
                return []

            # 3. Генерируем эмбеддинг запроса через Ollama
            query_embedding = await self._generate_embedding(query_text)

            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []

            # 4. Вычисляем сходство с каждым воспоминанием
            similarities = []

            for memory in all_memories:
                mem_id = memory.get("id")
                mem_text = memory.get("memory", "")

                if not mem_text:
                    continue

                # Получаем/генерируем эмбеддинг воспоминания
                if (
                    self.valves.cache_embeddings
                    and mem_id in self._memory_embeddings_cache
                ):
                    mem_embedding = self._memory_embeddings_cache[mem_id]
                else:
                    mem_embedding = await self._generate_embedding(mem_text)

                    if not mem_embedding:
                        logger.warning(
                            f"Failed to generate embedding for memory {mem_id}"
                        )
                        continue

                    if self.valves.cache_embeddings:
                        self._memory_embeddings_cache[mem_id] = mem_embedding

                # Косинусное сходство
                similarity = self._cosine_similarity(query_embedding, mem_embedding)

                similarities.append(
                    {"text": mem_text, "similarity": similarity, "id": mem_id}
                )

            # 5. Фильтруем по порогу и сортируем
            relevant = [
                item
                for item in similarities
                if item["similarity"] >= self.valves.vector_similarity_threshold
            ]

            relevant.sort(key=lambda x: x["similarity"], reverse=True)

            # 6. Берём топ-N
            top_memories = relevant[: self.valves.max_memories_to_inject]

            logger.debug(
                f"Selected {len(top_memories)} relevant memories (threshold: {self.valves.vector_similarity_threshold})"
            )

            # Логируем сходство для отладки
            for item in top_memories:
                logger.debug(
                    f"  - Similarity: {item['similarity']:.3f} | {item['text'][:50]}..."
                )

            return [item["text"] for item in top_memories]

        except Exception as e:
            logger.error(f"Error finding relevant memories: {e}", exc_info=True)
            return []

    def _format_chat_history_context(self, history_items: List[Dict[str, Any]]) -> str:
        """
        Форматирование релевантных старых сообщений для инъекции в промпт

        Args:
            history_items: Список сообщений с метаданными из _search_chat_history()

        Returns:
            str: Отформатированный контекст для системного промпта
        """
        if not history_items:
            return ""

        formatted_items = []
        for item in history_items:
            role = item["role"]
            summary = item["summary"]
            index = item["index"]
            similarity = item["similarity"]

            # Форматируем как диалог
            role_label = "User" if role == "user" else "Assistant"
            formatted_items.append(f"[Msg #{index}, relevance: {similarity:.2f}] {role_label}: {summary}")

        formatted = "\n".join(formatted_items)

        context = f"""

===== RELEVANT CONTEXT FROM EARLIER IN CONVERSATION =====
The following messages from earlier in this conversation may be relevant:

{formatted}

Use this context to maintain continuity and avoid repeating questions or losing track of earlier discussion.
===========================================================
"""
        return context

    def _format_memory_context(self, memories: List[str]) -> str:
        """Форматирование воспоминаний для инъекции в промпт"""

        if not memories:
            return ""

        format_type = self.valves.memory_display_format

        if format_type == "bullet":
            formatted = "\n".join([f"- {mem}" for mem in memories])
        elif format_type == "numbered":
            formatted = "\n".join([f"{i+1}. {mem}" for i, mem in enumerate(memories)])
        elif format_type == "paragraph":
            formatted = " ".join(memories)
        else:
            formatted = "\n".join(memories)

        context = f"""

===== RELEVANT USER MEMORIES =====
The following information about the user may be relevant to this conversation:

{formatted}

Use this information to personalize your response when appropriate.
==================================
"""
        return context

    def _inject_into_system_prompt(self, body: Dict[str, Any], context: str) -> None:
        """Добавляет контекст в системное сообщение"""

        if "messages" not in body:
            return

        messages = body["messages"]

        # Ищем существующее системное сообщение
        system_msg_index = None
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                system_msg_index = i
                break

        if system_msg_index is not None:
            # Добавляем к существующему
            messages[system_msg_index]["content"] += context
        else:
            # Создаём новое системное сообщение
            messages.insert(0, {"role": "system", "content": context})

    def _extract_memory_bank(self, memory_text: str) -> str:
        """Извлекает Memory Bank из текста воспоминания (если есть тег)"""

        import re

        # Ищем паттерн [Bank: Personal] или [Memory Bank: Work]
        match = re.search(r"\[(?:Memory )?Bank:\s*(\w+)\]", memory_text, re.IGNORECASE)

        if match:
            return match.group(1)

        return "General"  # По умолчанию

    async def add_memory(
        self,
        content: str,
        user_id: str,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> bool:
        """
        Добавляет новое знание/воспоминание в базу пользователя

        Args:
            content: Текст воспоминания для сохранения
            user_id: ID пользователя
            __event_emitter__: Эмиттер для отправки статуса

        Returns:
            bool: True если успешно, False при ошибке
        """

        if not Memories:
            logger.error("Memories model not available - running outside OpenWebUI?")
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "⚠️ Memory storage not available",
                            "done": True,
                        },
                    }
                )
            return False

        if not content or not content.strip():
            logger.warning("Cannot add empty memory")
            return False

        try:
            # Эмитим статус начала сохранения
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": "💾 Saving new memory...",
                            "done": False,
                        },
                    }
                )

            # Сохраняем воспоминание
            result = Memories.insert_new_memory(
                user_id=str(user_id),
                content=content.strip()
            )

            if result:
                logger.info(f"✅ Successfully saved memory for user {user_id}: {content[:50]}...")

                # Инвалидируем кэш эмбеддингов (т.к. появилось новое воспоминание)
                if self.valves.cache_embeddings and hasattr(result, 'id'):
                    # Кэш обновится автоматически при следующем поиске
                    logger.debug("Memory cache will be updated on next search")

                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "✅ Memory saved successfully",
                                "done": True,
                            },
                        }
                    )

                return True
            else:
                logger.error("Failed to save memory - insert returned None")
                if __event_emitter__:
                    await __event_emitter__(
                        {
                            "type": "status",
                            "data": {
                                "description": "⚠️ Failed to save memory",
                                "done": True,
                            },
                        }
                    )
                return False

        except Exception as e:
            logger.error(f"❌ Error saving memory: {e}", exc_info=True)
            if __event_emitter__:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"❌ Error saving memory: {str(e)}",
                            "done": True,
                        },
                    }
                )
            return False

    async def add_multiple_memories(
        self,
        memories: List[str],
        user_id: str,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> Dict[str, int]:
        """
        Добавляет несколько воспоминаний за раз

        Args:
            memories: Список текстов воспоминаний
            user_id: ID пользователя
            __event_emitter__: Эмиттер для отправки статуса

        Returns:
            Dict с количеством успешных/неуспешных операций
        """

        if not memories:
            return {"success": 0, "failed": 0, "total": 0}

        success_count = 0
        failed_count = 0

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"💾 Saving {len(memories)} memories...",
                        "done": False,
                    },
                }
            )

        for i, memory in enumerate(memories, 1):
            logger.debug(f"Saving memory {i}/{len(memories)}")

            result = await self.add_memory(
                content=memory,
                user_id=user_id,
                __event_emitter__=None  # Не эмитим статус для каждого
            )

            if result:
                success_count += 1
            else:
                failed_count += 1

        # Итоговый статус
        if __event_emitter__:
            if failed_count == 0:
                status_msg = f"✅ Saved {success_count} memories successfully"
            else:
                status_msg = f"⚠️ Saved {success_count}/{len(memories)} memories ({failed_count} failed)"

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": status_msg,
                        "done": True,
                    },
                }
            )

        logger.info(f"Batch memory save complete: {success_count} success, {failed_count} failed")

        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(memories)
        }

    async def __del__(self):
        """Cleanup при удалении фильтра"""
        if self._session and not self._session.closed:
            await self._session.close()
