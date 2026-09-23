from pydantic import BaseModel, Field

from app.tools.base_tool import BaseTool


class AskHumanInput(BaseModel):
    question: str = Field(description="向用户提出的问题")


class AskHumanTool(BaseTool):
    name: str = "ask_human"
    description: str = (
        "向用户询问缺失信息、确认偏好或获取反馈。调用后暂停当前运行，等待用户通过 reply 接口回答。"
    )
    parameters: type[BaseModel] = AskHumanInput

    async def execute(self, question: str) -> str:
        return question
