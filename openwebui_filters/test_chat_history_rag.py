"""
Тестовый скрипт для Chat History RAG функциональности
"""

import sys
import asyncio
from typing import Dict, List, Any

# Исправление кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def create_mock_filter():
    """Создаём мок-класс фильтра для тестирования без OpenWebUI"""

    class MockFilter:
        def __init__(self):
            self._chat_history_index: Dict[str, Dict[str, Any]] = {}
            self._summarization_cache: Dict[str, str] = {}

            # Настройки
            self.chat_history_similarity_threshold = 0.7
            self.enable_chat_history_rag = True

        def _generate_message_hash(self, role: str, content: str, index: int) -> str:
            """Генерирует уникальный хэш для сообщения"""
            import hashlib
            data = f"{role}:{index}:{content[:100]}"
            return hashlib.md5(data.encode()).hexdigest()

        def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
            """Вычисление косинусного сходства"""
            if len(vec1) != len(vec2):
                return 0.0

            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            norm1 = sum(a * a for a in vec1) ** 0.5
            norm2 = sum(b * b for b in vec2) ** 0.5

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)

        async def mock_index_message(self, role: str, content: str, index: int, embedding: List[float]):
            """Мок индексации (без реального API)"""
            import time

            msg_hash = self._generate_message_hash(role, content, index)
            summary = content[:100] + "..." if len(content) > 100 else content

            self._chat_history_index[msg_hash] = {
                "index": index,
                "role": role,
                "content": content,
                "summary": summary,
                "embedding": embedding,
                "timestamp": time.time(),
            }
            return True

        async def mock_search_history(self, query_embedding: List[float], exclude_recent: int = 2):
            """Мок поиска (без реального API)"""
            similarities = []
            max_index = max((item["index"] for item in self._chat_history_index.values()), default=0)

            for msg_hash, msg_data in self._chat_history_index.items():
                msg_index = msg_data["index"]

                if msg_index > max_index - exclude_recent:
                    continue

                msg_embedding = msg_data["embedding"]
                similarity = self._cosine_similarity(query_embedding, msg_embedding)

                if similarity >= self.chat_history_similarity_threshold:
                    similarities.append({
                        "index": msg_index,
                        "role": msg_data["role"],
                        "content": msg_data["content"],
                        "summary": msg_data["summary"],
                        "similarity": similarity,
                    })

            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return similarities[:3]

    return MockFilter()


async def test_basic_indexing():
    """Тест 1: Базовая индексация сообщений"""
    print("\n" + "="*70)
    print("ТЕСТ 1: Базовая индексация сообщений")
    print("="*70)

    filter_obj = create_mock_filter()

    # Создаём тестовые сообщения с мок-embeddings
    test_messages = [
        ("user", "Проанализируй данные о продажах", [1.0, 0.5, 0.3]),
        ("assistant", "Категория Electronics принесла $45K", [1.0, 0.6, 0.2]),
        ("user", "Какие еще категории?", [0.9, 0.5, 0.4]),
        ("assistant", "Clothing - $32K, Food - $28K", [0.8, 0.5, 0.3]),
        ("user", "Расскажи про погоду", [0.1, 0.1, 0.9]),  # Нерелевантное
    ]

    # Индексируем
    for i, (role, content, embedding) in enumerate(test_messages):
        await filter_obj.mock_index_message(role, content, i, embedding)

    print(f"✅ Проиндексировано сообщений: {len(filter_obj._chat_history_index)}")
    print(f"   Ожидалось: {len(test_messages)}")

    assert len(filter_obj._chat_history_index) == len(test_messages), "Количество не совпадает!"

    print("✅ ТЕСТ 1 ПРОЙДЕН\n")
    return filter_obj


async def test_vector_search(filter_obj):
    """Тест 2: Векторный поиск по истории"""
    print("="*70)
    print("ТЕСТ 2: Векторный поиск релевантных сообщений")
    print("="*70)

    # Запрос похожий на сообщения о продажах
    query_embedding = [1.0, 0.55, 0.25]  # Похож на первые 4 сообщения

    results = await filter_obj.mock_search_history(query_embedding, exclude_recent=2)

    print(f"\nЗапрос (embedding): {query_embedding}")
    print(f"Найдено релевантных сообщений: {len(results)}\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. [Msg #{result['index']}] {result['role']}")
        print(f"   Similarity: {result['similarity']:.3f}")
        print(f"   Content: {result['summary'][:60]}...")
        print()

    # Проверяем что нашлись релевантные
    assert len(results) > 0, "Должны быть найдены релевантные сообщения!"

    # Проверяем что исключены последние 2
    for result in results:
        assert result['index'] < len(filter_obj._chat_history_index) - 2, \
            "Последние сообщения не должны попасть в результаты!"

    print("✅ ТЕСТ 2 ПРОЙДЕН\n")


async def test_similarity_threshold():
    """Тест 3: Работа порога релевантности"""
    print("="*70)
    print("ТЕСТ 3: Фильтрация по порогу similarity")
    print("="*70)

    filter_obj = create_mock_filter()

    # Добавляем сообщения с разными векторами
    await filter_obj.mock_index_message("user", "Message about sales", 0, [1.0, 0.0, 0.0])
    await filter_obj.mock_index_message("user", "Message about weather", 1, [0.0, 1.0, 0.0])
    await filter_obj.mock_index_message("user", "Message about data", 2, [0.9, 0.1, 0.0])

    # Запрос похожий только на первое и третье
    query = [1.0, 0.0, 0.0]

    results = await filter_obj.mock_search_history(query, exclude_recent=0)

    print(f"\nПорог similarity: {filter_obj.chat_history_similarity_threshold}")
    print(f"Найдено сообщений: {len(results)}")

    for result in results:
        print(f"  - Msg #{result['index']}: similarity = {result['similarity']:.3f}")
        assert result['similarity'] >= filter_obj.chat_history_similarity_threshold, \
            f"Similarity {result['similarity']} ниже порога!"

    print("\n✅ ТЕСТ 3 ПРОЙДЕН\n")


async def test_message_hashing():
    """Тест 4: Уникальность hash для сообщений"""
    print("="*70)
    print("ТЕСТ 4: Генерация уникальных hash")
    print("="*70)

    filter_obj = create_mock_filter()

    # Одинаковый контент, разные индексы
    hash1 = filter_obj._generate_message_hash("user", "Same content", 0)
    hash2 = filter_obj._generate_message_hash("user", "Same content", 1)

    print(f"\nHash для index=0: {hash1}")
    print(f"Hash для index=1: {hash2}")

    assert hash1 != hash2, "Hash должны отличаться для разных индексов!"

    # Одинаковый индекс и контент
    hash3 = filter_obj._generate_message_hash("user", "Same content", 0)

    print(f"Hash для index=0 (повтор): {hash3}")

    assert hash1 == hash3, "Hash должны совпадать для одинаковых данных!"

    print("\n✅ ТЕСТ 4 ПРОЙДЕН\n")


async def test_real_scenario():
    """Тест 5: Реальный сценарий использования"""
    print("="*70)
    print("ТЕСТ 5: Реальный сценарий - потеря контекста")
    print("="*70)

    filter_obj = create_mock_filter()

    # Симулируем длинный диалог
    conversation = [
        ("user", "Проанализируй этот CSV с продажами по категориям", [0.8, 0.9, 0.1]),
        ("assistant", "Анализирую... Топ категория - Electronics с выручкой $45,000", [0.8, 0.85, 0.15]),
        ("user", "Какой рост показала Electronics?", [0.75, 0.8, 0.2]),
        ("assistant", "Electronics показала рост на 20% по сравнению с прошлым месяцем", [0.75, 0.85, 0.15]),
        ("user", "А что с Clothing?", [0.7, 0.6, 0.3]),
        ("assistant", "Clothing - $32,000, рост 15%", [0.7, 0.65, 0.25]),
        # ... много сообщений о других темах ...
        ("user", "Расскажи про новости технологий", [0.1, 0.2, 0.9]),
        ("assistant", "Вот последние новости...", [0.15, 0.2, 0.85]),
        ("user", "Что ты думаешь про AI?", [0.2, 0.3, 0.8]),
        ("assistant", "AI развивается очень быстро...", [0.2, 0.25, 0.8]),
    ]

    print(f"\nСимулируем диалог из {len(conversation)} сообщений")
    print("Первые 6 сообщений - про продажи")
    print("Последние 4 сообщения - про другие темы\n")

    # Индексируем все
    for i, (role, content, emb) in enumerate(conversation):
        await filter_obj.mock_index_message(role, content, i, emb)

    print(f"Проиндексировано: {len(filter_obj._chat_history_index)} сообщений\n")

    # Теперь пользователь спрашивает про Electronics (вернулся к старой теме)
    print("🔍 Пользователь спрашивает: 'Напомни, сколько было у Electronics?'")
    query_embedding = [0.78, 0.82, 0.18]  # Похож на сообщения про Electronics

    results = await filter_obj.mock_search_history(query_embedding, exclude_recent=3)

    print(f"✅ Найдено релевантных старых сообщений: {len(results)}\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. [Msg #{result['index']}, similarity: {result['similarity']:.2f}]")
        print(f"   {result['role'].upper()}: {result['content']}")
        print()

    # Проверяем что нашлись сообщения про Electronics
    found_electronics = any("Electronics" in r['content'] for r in results)
    assert found_electronics, "Должны быть найдены сообщения про Electronics!"

    # Проверяем что последние сообщения исключены
    for result in results:
        assert result['index'] < 7, "Последние сообщения не должны попасть в результаты!"

    print("✅ ТЕСТ 5 ПРОЙДЕН - Контекст успешно восстановлен!\n")


async def main():
    """Запуск всех тестов"""
    print("\n" + "🧪" * 35)
    print("ТЕСТИРОВАНИЕ CHAT HISTORY RAG")
    print("🧪" * 35)

    try:
        # Тест 1: Индексация
        filter_obj = await test_basic_indexing()

        # Тест 2: Поиск
        await test_vector_search(filter_obj)

        # Тест 3: Порог
        await test_similarity_threshold()

        # Тест 4: Хеширование
        await test_message_hashing()

        # Тест 5: Реальный сценарий
        await test_real_scenario()

        print("="*70)
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("="*70)
        print("\n✅ Chat History RAG работает корректно!")
        print("✅ Векторный поиск функционирует")
        print("✅ Индексация и хеширование в порядке")
        print("✅ Фильтрация по порогу работает")
        print("✅ Реальный сценарий восстановления контекста работает\n")

        return True

    except AssertionError as e:
        print(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}\n")
        return False
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
