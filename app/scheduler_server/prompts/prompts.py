from typing import List

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import Prompt, base


class Prompts:
    """
    Prompt provider that registers instance methods as MCP prompts.

    Usage:
        Prompts(mcp)  # registers prompts on init
    """

    def __init__(self, mcp_instance: FastMCP) -> None:
        # simple_prompt(query: str) -> str
        mcp_instance.add_prompt(
            Prompt.from_function(
                self.simple_prompt,
                name="simple_prompt",
                description=(
                    "Return a single text prompt asking for "
                    "a detailed, step-by-step answer."
                ),
            )
        )

        # structured_prompt(code: str, language: str = "python") -> list[base.Message]
        mcp_instance.add_prompt(
            Prompt.from_function(
                self.structured_prompt,
                name="structured_prompt",
                description=(
                    "Return a small conversation (list of messages) to guide "
                    "code review. Includes user and assistant turns."
                ),
            )
        )

        # data_analysis_prompt(data: str, objective: str) -> list[base.Message]
        mcp_instance.add_prompt(
            Prompt.from_function(
                self.data_analysis_prompt,
                name="data_analysis_prompt",
                description=(
                    "Return a structured prompt for data analysis, including "
                    "the objective and raw data."
                ),
            )
        )

        # image_analysis_prompt(image_description, analysis_type) -> str
        mcp_instance.add_prompt(
            Prompt.from_function(
                self.image_analysis_prompt,
                name="image_analysis_prompt",
                description=(
                    "Return a text prompt instructing an image analysis with "
                    "a selectable focus (general, technical, content, sentiment)."
                ),
            )
        )

    # --- Prompt methods ---

    def simple_prompt(self, query: str) -> str:
        """
        A simple text prompt that returns a single formatted string.
        """
        return f"""
        Please provide a detailed answer to the following question:

        {query}

        Take your time to think step by step and provide a comprehensive response.
        """

    def structured_prompt(
        self, code: str, language: str = "python"
    ) -> List[base.Message]:
        """
        A structured prompt using Message objects to simulate a short dialogue.
        """
        return [
            base.UserMessage(f"I need help reviewing this {language} code:"),
            base.UserMessage(f"```{language}\n{code}\n```"),
            base.AssistantMessage(
                "I'll analyze this code for you. What specific aspects "
                "would you like me to focus on?"
            ),
            base.UserMessage(
                "Please focus on code quality, potential bugs, and performance issues."
            ),
        ]

    def data_analysis_prompt(self, data: str, objective: str) -> List[base.Message]:
        """
        A prompt for data analysis tasks with a clear objective and raw data.
        """
        return [
            base.UserMessage("I need help analyzing some data."),
            base.UserMessage(f"Objective: {objective}"),
            base.UserMessage("Here's the data:"),
            base.UserMessage(data),
            base.UserMessage(
                "Please analyze this data and provide "
                "insights that address my objective."
            ),
        ]

    def image_analysis_prompt(
        self, image_description: str, analysis_type: str = "general"
    ) -> str:
        """
        A prompt for image analysis with configurable analysis focus.
        """
        instructions = {
            "general": (
                "Provide a general description and analysis "
                "of what you see in the image."
            ),
            "technical": (
                "Provide a technical analysis of the image, focusing on composition, "
                "lighting, and techniques used."
            ),
            "content": (
                "Analyze the content of the image, identifying objects, "
                "people, and activities."
            ),
            "sentiment": "Analyze the mood and emotional impact of the image.",
        }
        instruction = instructions.get(analysis_type, instructions["general"])

        return f"""
        I'm showing you an image with the following description:

        {image_description}

        {instruction}
        """
