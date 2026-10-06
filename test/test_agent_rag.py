import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.agent.support_agent import SupportAgent


async def main():
    questions = [
        "现在几点"
        "",
    ]
    for q in questions:
        agent = SupportAgent()
        print(f"\n{'='*50}\n用户: {q}")
        answer = await agent.run(q)
        print("\n=== Agent 最终回复 ===")
        print(answer)

        print("\n=== 记忆轨迹（调试）===")
        for m in agent.memory.messages:
            role = m.role
            tc_names = ""
            if getattr(m, "tool_calls", None):
                tc_names = " [调用工具: " + ", ".join(tc.function.name for tc in m.tool_calls) + "]"
            preview = (m.content or "")[:50].replace("\n", " ")
            print(f"[{role}]{tc_names} {preview}")


if __name__ == "__main__":
    asyncio.run(main())
