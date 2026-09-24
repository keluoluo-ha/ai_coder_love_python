# app/llm.py
from openai import OpenAI
import os
from app.advisor.logger_advisor import LoggerAdvisor
from app.schema import Message


class LLM:
    def __init__(self, model="qwen-plus"):
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = model
        self.logger_advisor = LoggerAdvisor()

    def ask_tool(self, messages, system_msgs=None, tools=None):
        # 1. 合并 system_msgs + messages
        if system_msgs is not None:
            # 利用之前重载的 + 运算符：系统消息在前，历史消息在后
            full_messages = system_msgs + messages
        else:
            full_messages = messages
        # 2. 每个 Message 调 to_dict() 转成 dict 列表
        payload_messages = [msg.to_dict() for msg in full_messages]
        # 3. 调 openai client.chat.completions.create
        kwargs = {
            "model": self.model,
            "messages": payload_messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.logger_advisor.around(
            "ask_tool",
            self.model,
            full_messages,
            tools,
            lambda: self.client.chat.completions.create(**kwargs),
        )
        # 4. 取 response.choices[0].message 返回（含 content + tool_calls）
        return response.choices[0].message

    def ask_tool_stream(self, messages, system_msgs=None, tools=None):
        """流式版：stream=True 时 LLM 逐 chunk 吐 token，这里边收边 yield。"""
        if system_msgs is not None:
            full_messages = system_msgs + messages
        else:
            full_messages = messages
        payload_messages = [msg.to_dict() for msg in full_messages]
        kwargs = {"model": self.model, "messages": payload_messages, "stream": True}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        started_at = self.logger_advisor.before("ask_tool_stream", self.model, full_messages, tools)
        try:
            stream = self.client.chat.completions.create(**kwargs)
            tool_calls_acc = {}  # index -> {"id", "name", "arguments"}
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:
                    yield ("text", delta.content)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {"id": tc.id or f"call_{idx}", "name": "", "arguments": ""}
                        if tc.function:
                            if tc.function.name:
                                tool_calls_acc[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_acc[idx]["arguments"] += tc.function.arguments
            if tool_calls_acc:
                yield ("tool_calls", [tool_calls_acc[i] for i in sorted(tool_calls_acc)])
            self.logger_advisor.after("ask_tool_stream", started_at)
        except Exception as exc:
            self.logger_advisor.after("ask_tool_stream", started_at, error=exc)
            raise
