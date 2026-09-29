from app.tools.base_tool import BaseTool
from pydantic import BaseModel



class TerminateInput(BaseModel):
    pass

class TerminateTool(BaseTool):
    name: str = "terminate"
    description: str = "当任务完成、问题已解决、或用户明确表示结束时，调用此工具终止当前会话。"
    parameters:type[BaseModel]=TerminateInput

    async def execute(self, **kwargs) -> str:
        return "对话已结束。"
