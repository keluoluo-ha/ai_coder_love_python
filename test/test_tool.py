# test/test_tool.py
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from app.tools.DateTimeTool import DateTimeTool

tool = DateTimeTool()

# 1. 测试 to_param() — 看生成的 JSON 对不对
print("=== to_param() ===")
import json
print(json.dumps(tool.to_param(), indent=2, ensure_ascii=False))

# 2. 测试 execute() — 看工具能不能执行
print("\n=== execute() ===")
result = asyncio.run(tool())
print(result)
