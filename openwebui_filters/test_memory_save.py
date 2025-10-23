"""
Тестовый скрипт для проверки функции сохранения знаний
"""

import re
import sys
from typing import Optional

# Исправление кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def is_memory_save_request(message: str) -> Optional[str]:
    """
    Определяет, является ли сообщение запросом на сохранение знания
    (копия функции из фильтра для тестирования)
    """
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


def test_memory_detection():
    """Тест распознавания команд сохранения"""

    # Тестовые примеры
    test_cases = [
        # (входное сообщение, ожидаемый результат)
        ("запомни что я люблю пиццу", "я люблю пиццу"),
        ("сохрани знание: мой день рождения 15 марта", "мой день рождения 15 марта"),
        ("добавь в память: я работаю программистом", "я работаю программистом"),
        ("remember that I like pizza", "i like pizza"),
        ("save to memory: my birthday is March 15", "my birthday is march 15"),
        ("memorize: I work as a developer", "i work as a developer"),
        ("обычное сообщение без команды", None),
        ("как дела?", None),
        ("what's the weather today?", None),
    ]

    print("🧪 Тестирование распознавания команд сохранения\n")
    print("=" * 70)

    passed = 0
    failed = 0

    for message, expected in test_cases:
        result = is_memory_save_request(message)

        # Сравниваем (игнорируя регистр для простоты)
        result_lower = result.lower() if result else None
        expected_lower = expected.lower() if expected else None

        is_correct = result_lower == expected_lower

        status = "✅" if is_correct else "❌"

        print(f"\n{status} Сообщение: {message}")
        print(f"   Ожидалось: {expected}")
        print(f"   Получено:  {result}")

        if is_correct:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 70)
    print(f"\n📊 Результаты: {passed} успешно, {failed} провалено")
    print(f"   Процент успеха: {(passed / len(test_cases) * 100):.1f}%")

    return failed == 0


if __name__ == "__main__":
    success = test_memory_detection()
    sys.exit(0 if success else 1)
