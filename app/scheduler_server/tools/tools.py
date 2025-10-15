"""Scheduler Server Tools - напоминания и автоматические задания"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP


class Tools:
    """
    Scheduler Server Tools - управление расписанием напоминаний и ритуалов.

    Функции:
    - add_rule: добавить правило напоминания с cron расписанием
    - list_rules: получить список всех правил
    - remove_rule: удалить правило по ID
    - trigger_now: запустить правило немедленно (для тестирования)
    """

    def __init__(self, mcp_instance: FastMCP) -> None:
        # add_rule(cron: str, prompt: str, description: str | None) -> dict
        mcp_instance.add_tool(
            self.add_rule,
            name="add_rule",
            description=(
                "Добавить новое правило напоминания с cron расписанием и текстом промпта. "
                "Например: '0 9 * * *' для ежедневного напоминания в 9:00."
            ),
        )

        # list_rules() -> list[dict]
        mcp_instance.add_tool(
            self.list_rules,
            name="list_rules",
            description="Получить список всех активных правил напоминаний.",
        )

        # remove_rule(rule_id: int) -> dict
        mcp_instance.add_tool(
            self.remove_rule,
            name="remove_rule",
            description="Удалить правило напоминания по его ID.",
        )

        # trigger_now(rule_id: int) -> dict
        mcp_instance.add_tool(
            self.trigger_now,
            name="trigger_now",
            description=(
                "Запустить правило немедленно (полезно для тестирования). "
                "Не влияет на обычное расписание."
            ),
        )

    # -------- tool methods --------

    async def add_rule(
        self,
        cron: str,
        prompt: str,
        description: Optional[str] = None,
        ctx: Context = None,
    ) -> Dict[str, Any]:
        """
        Добавить новое правило напоминания.

        Args:
            cron: Cron выражение (например, '0 9 * * *')
            prompt: Текст промпта для отправки
            description: Описание правила (опционально)
            ctx: MCP Context

        Returns:
            Информация о созданном правиле
        """
        # TODO: Реализовать сохранение в PostgreSQL и регистрацию в планировщике
        pass

    async def list_rules(self, ctx: Context = None) -> List[Dict[str, Any]]:
        """
        Получить список всех правил.

        Args:
            ctx: MCP Context

        Returns:
            Список словарей с информацией о правилах
        """
        # TODO: Реализовать получение из PostgreSQL
        pass

    async def remove_rule(
        self, rule_id: int, ctx: Context = None
    ) -> Dict[str, Any]:
        """
        Удалить правило по ID.

        Args:
            rule_id: ID правила для удаления
            ctx: MCP Context

        Returns:
            Результат удаления
        """
        # TODO: Реализовать удаление из PostgreSQL и планировщика
        pass

    async def trigger_now(
        self, rule_id: int, ctx: Context = None
    ) -> Dict[str, Any]:
        """
        Запустить правило немедленно.

        Args:
            rule_id: ID правила для запуска
            ctx: MCP Context

        Returns:
            Результат выполнения
        """
        # TODO: Реализовать немедленное выполнение правила
        pass
