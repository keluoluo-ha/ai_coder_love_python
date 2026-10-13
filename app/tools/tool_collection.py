from typing import Any

from langchain_core.tools import BaseTool


class ToolCollection:
    """聚合一组 LangChain Tool，供 Agent 以 function calling 形式使用"""

    def __init__(self, *tools: BaseTool):
        self.tools = list(tools)
        self.tool_map = {t.name: t for t in self.tools}

    def to_params(self) -> list[dict[str, Any]]:
        """所有工具 -> OpenAI function calling 参数（由 LangChain 转换）"""
        return [t.to_param() for t in self.tools]

    def to_langchain_tools(self) -> list[BaseTool]:
        """原生 LangChain 工具列表，将来可直接 llm.bind_tools(...)"""
        return list(self.tools)

    async def execute(self, name: str, tool_input: dict[str, Any]) -> Any:
        """通过 LangChain 的 ainvoke 执行工具（含 Pydantic 参数校验）"""
        tool = self.tool_map[name]
        return await tool.ainvoke(tool_input)
