import sys
from pathlib import Path
# 将项目根目录加入搜索路径
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from langchain_core.messages import HumanMessage, AIMessage
from app.chatmemory.FileChatMemory import FileChatMemory

memory = FileChatMemory("test-001")
memory.add_message(HumanMessage("退换货政策是什么？"))
memory.add_message(AIMessage("7天内无理由退换。"))
print(memory.messages)   # 应该打印两条消息
memory.clear()
print(memory.messages)   # 应该打印空列表 []
