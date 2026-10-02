import json
from abc import ABC, abstractmethod
from app.schema import AgentState, Memory, Message


class BaseAgent(ABC):
    name: str
    system_prompt: str = ""
    next_prompt: str = ""

    state: AgentState = AgentState.IDLE
    max_steps: int = 10
    current_steps: int = 0
    memory: Memory

    def __init__(self):
        self.memory = Memory()

    async def run(self, user_prompt: str = None) -> str:
        self.state = AgentState.RUNNING
        if user_prompt:
            self.update_memory("user", user_prompt)

        while self.current_steps < self.max_steps and self.state != AgentState.FINISHED:
            self.current_steps += 1
            step_result = await self.step()

            if self.state == AgentState.WAITING_FOR_HUMAN:
                return step_result

            if self.state == AgentState.FINISHED:
                return step_result

        return "已达到最大步数，对话结束"

    async def run_stream(self, user_prompt: str = None):
        """流式版主循环：把 think_stream 产出的 token 逐个 yield 出去。"""
        self.state = AgentState.RUNNING
        if user_prompt:
            self.update_memory("user", user_prompt)

        while self.current_steps < self.max_steps and self.state != AgentState.FINISHED:
            self.current_steps += 1
            self.tool_calls_buffer = []  # 每步重置

            # think_stream 把文本 token 逐个 yield，这里直接转发成事件
            async for token in self.think_stream():
                yield {"type": "text", "content": token}

            if self.tool_calls_buffer:  # 这步是要调工具
                action_result = await self.act()
                if self.state == AgentState.WAITING_FOR_HUMAN:
                    payload = json.loads(action_result.split("__ASK_HUMAN__:", 1)[1].strip())
                    yield {"type": "ask_human", "data": {
                        "question": payload.get("question"),
                        "options": payload.get("options", []),
                        "status": "WAITING",
                    }}
                    yield {"type": "done"}
                    return
                if self.state == AgentState.FINISHED:
                    yield {"type": "done"}
                    return
                # 否则继续循环（工具结果已入 memory）
            else:  # 纯文本，token 已流完
                self.state = AgentState.FINISHED
                yield {"type": "done"}
                return

        yield {"type": "text", "content": "已达到最大步数，对话结束"}
        yield {"type": "done"}

    def update_memory(self, role: str, content: str):
        """往 memory 里加一条 Message"""
        message = Message(role=role, content=content)
        self.memory.add_message(message)

    @abstractmethod
    async def step(self) -> str:
        """子类实现：think + act"""
