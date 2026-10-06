import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv()


from app.agent.support_agent import SupportAgent


async def main():
    print("=== 测试1: 纯对话 ===")
    agent = SupportAgent()
    r1 = await agent.run("你好，你是谁？")
    print("回复:", r1)

    print("\n=== 测试2: 调用时间工具 ===")
    agent2 = SupportAgent()
    r2 = await agent2.run("现在几点了？")
    print("回复:", r2)


if __name__ == "__main__":
    asyncio.run(main())
