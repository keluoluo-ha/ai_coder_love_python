from langchain_core.messages import HumanMessage, AIMessage
from app.chatmemory.MySQLChatMemory import MySqlChatMemory
from app.config import DATABASE_URL

memory = MySqlChatMemory("test-001", DATABASE_URL)
memory.add_message(HumanMessage("退换货政策是什么？"))
memory.add_message(AIMessage("7天内无理由退换。"))
print(memory.messages)   # 两条
memory.clear()
print(memory.messages)   # 空列表
