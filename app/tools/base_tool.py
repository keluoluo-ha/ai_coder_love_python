"""工具基类：继承 LangChain 的 BaseTool（Tool Calling）。

之前是自研 BaseTool + 手写 OpenAI function calling 参数，
现在统一迁移到 LangChain Tool Calling：
- 工具即 langchain_core.tools.BaseTool 子类；
- 参数 schema 用 Pydantic 模型声明在 args_schema，由 LangChain 负责校验；
- 工具 -> OpenAI function calling 参数的转换由 LangChain 官方
  convert_to_openai_function 完成。
"""
from typing import Any, Dict

from langchain_core.tools import BaseTool as LangChainBaseTool
from langchain_core.utils.function_calling import convert_to_openai_function


class BaseTool(LangChainBaseTool):
    """项目工具基类 = LangChain BaseTool + 旧接口兼容方法"""

    def to_param(self) -> Dict[str, Any]:
        """兼容旧接口：LangChain 工具 -> OpenAI function calling JSON"""
        return convert_to_openai_function(self)

    async def __call__(self, **kwargs) -> Any:
        """兼容旧调用方式 await tool(x=...)，走 LangChain 异步执行与参数校验"""
        return await self.ainvoke(kwargs)
