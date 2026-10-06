# test/test_llm.py
from dotenv import load_dotenv
load_dotenv()

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.llm import LLM
from app.schema import Message

llm = LLM()

# 一段简单对话
messages = [
    Message.user_message("你好，请用一句话介绍自己"),
]

resp = llm.ask_tool(messages)
print("=== 不带工具的回复 ===")
print(f"content: {resp.content}")


# 接上面继续
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"}
                },
                "required": ["city"]
            }
        }
    }
]

messages2 = [
    Message.user_message("北京今天天气怎么样？"),
]

resp2 = llm.ask_tool(messages2, tools=tools)
print("\n=== 带工具的回复 ===")
print(f"content: {resp2.content}")
print(f"tool_calls: {resp2.tool_calls}")

