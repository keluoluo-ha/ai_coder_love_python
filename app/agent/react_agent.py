
from abc import abstractmethod

from app.agent.base import BaseAgent
from app.schema import AgentState


class ReActAgent(BaseAgent):

  last_step_answer:str=""

  async def step(self)->str:
    self.last_step_answer=""
    try:
      ThinkResult=await self.think()
      if not ThinkResult:
        if self.state!=AgentState.WAITING_FOR_HUMAN:
          self.state=AgentState.FINISHED
        return self.last_step_answer or "思考完成。"
      action_result=await self.act()
      if action_result is None:
        return ""
      return action_result
    except Exception as e:
      self.state=AgentState.FINISHED
      return f"步骤执行失败：{e}"

  @abstractmethod
  async def think(self)->bool:
    """子类实现思考"""

  @abstractmethod
  async def act(self)->str:
    """子类实现行动"""
    