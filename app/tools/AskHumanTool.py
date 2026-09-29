from pydantic import BaseModel, Field
from app.tools.base_tool import BaseTool


# 调用 ask_human 工具，必须传入字段 question，字段含义是向用户提出的问题。
# 没有它，大模型经常忘记传参、参数名字写错，工具调用失败。

class AskHumanInput(BaseModel):
    question: str = Field(description="向用户提出的问题")

class AskHumanTool(BaseTool):
  name:str="ask_human"
  description:str=(
        """【必须使用的工具】向用户询问缺失信息、确认偏好或获取反馈。
            当任务缺少关键信息、存在歧义、或执行不可逆操作前需要用户确认时，必须调用本工具，禁止只在回复文本里提问。
            调用后任务会暂停，等待用户回答再继续。"""
    )
  parameters:type[BaseModel]=AskHumanInput
  

  async def execute(self,question:str)->str:
      print(f"\n[Agent 提问]：{question}")
      answer = input("[你的回答]：")
      return answer