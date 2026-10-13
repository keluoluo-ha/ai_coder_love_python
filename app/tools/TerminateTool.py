from pydantic import BaseModel

from app.tools.base_tool import BaseTool


class TerminateInput(BaseModel):
    pass


class TerminateTool(BaseTool):
    name: str = "terminate"
    description: str = "当任务完成、问题已解决、或用户明确表示结束时，调用此工具终止当前会话。"
    args_schema: type[BaseModel] = TerminateInput

    def _run(self, **kwargs) -> str:
        return "对话已结束。"

    async def _arun(self, **kwargs) -> str:
        return self._run()
