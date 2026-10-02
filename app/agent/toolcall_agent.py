import json
from app.agent.react_agent import ReActAgent
from app.llm import LLM
from app.schema import AgentState, Message, ToolCall, Function
from app.tools.tool_collection import ToolCollection


class ToolCallAgent(ReActAgent):
    def __init__(self, tools: ToolCollection):
        super().__init__()
        self.available_tools = tools
        self.llm = LLM()
        self.tool_calls_buffer = []

    # 把 system_prompt + next_step_prompt 拼成系统消息
    def _build_system_msgs(self):
        msgs = []
        if self.system_prompt:
            msgs.append(Message.system_message(self.system_prompt))
        if self.next_prompt:
            msgs.append(Message.system_message(self.next_prompt))
        return msgs

    # think：调 LLM，解析是否要调工具（非流式版，测试仍在用）
    async def think(self) -> bool:
        sys_msgs = self._build_system_msgs()
        resp = self.llm.ask_tool(
            messages=self.memory.messages,
            system_msgs=sys_msgs,
            tools=self.available_tools.to_params(),
        )
        content = resp.content or ""
        tool_calls = resp.tool_calls or []

        if tool_calls:
            assistant_msg = Message.from_tool_calls(tool_calls, content)
            self.memory.add_message(assistant_msg)
            self.tool_calls_buffer = tool_calls
            return True  # -> 需要执行工具
        self.memory.add_message(Message.assistant_message(content))
        self.last_step_answer = content
        return False

    # think_stream：流式版，把文本 token 逐个 yield；有工具调用就拼好 buffer
    async def think_stream(self):
        sys_msgs = self._build_system_msgs()
        text_parts = []
        tool_calls_dicts = None

        for kind, payload in self.llm.ask_tool_stream(
            messages=self.memory.messages,
            system_msgs=sys_msgs,
            tools=self.available_tools.to_params(),
        ):
            if kind == "text":
                text_parts.append(payload)
                yield payload  # 直接把 token 抛给上层（打字机来源）
            elif kind == "tool_calls":
                tool_calls_dicts = payload

        full_content = "".join(text_parts)

        if tool_calls_dicts:
            calls = [
                ToolCall(id=d["id"], function=Function(name=d["name"], arguments=d["arguments"]))
                for d in tool_calls_dicts
            ]
            self.memory.add_message(Message.from_tool_calls(calls, full_content))
            self.tool_calls_buffer = calls
        else:
            self.memory.add_message(Message.assistant_message(full_content))
            self.last_step_answer = full_content

    # act：执行工具，处理 AskHuman + Terminate
    async def act(self) -> str:
        for tc in self.tool_calls_buffer:
            name = tc.function.name
            args = json.loads(tc.function.arguments)

            if name == "ask_human":
                self.state = AgentState.WAITING_FOR_HUMAN
                return "__ASK_HUMAN__: " + json.dumps(args, ensure_ascii=False)

            # 执行工具
            result = await self.available_tools.execute(name, args)
            self.memory.add_message(Message.tool_message(str(result), name, tc.id))

            # Terminate
            if name == "terminate":
                self.state = AgentState.FINISHED
                return str(result)

        return None
