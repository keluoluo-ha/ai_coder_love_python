from app.agent.toolcall_agent import ToolCallAgent
from app.tools.AskHumanTool import AskHumanTool
from app.tools.RAGSearchTool import RAGSearchTool
from app.tools.WebSearchTool import WebSearchTool
from app.tools.DateTimeTool import DateTimeTool
from app.tools.TerminateTool import TerminateTool
from app.tools.tool_collection import ToolCollection
from app.prompts import SYSTEM_PROMPT, NEXT_STEP_PROMPT



class SupportAgent(ToolCallAgent):
    def __init__(self):
        # 1. 组装 5 个工具
        tools = ToolCollection(
            DateTimeTool(),
            WebSearchTool(),
            RAGSearchTool(),
            AskHumanTool(),
            TerminateTool(),
        )
        # 2. 传给父类 → 父类存为 self.available_tools
        super().__init__(tools)
        
        # 3. 设角色 prompt（提示词统一放在 app/prompts.py）
        self.system_prompt = SYSTEM_PROMPT
        self.next_prompt = NEXT_STEP_PROMPT
