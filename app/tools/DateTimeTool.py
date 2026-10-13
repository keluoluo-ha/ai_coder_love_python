from datetime import datetime

from pydantic import BaseModel

from app.tools.base_tool import BaseTool


class DateTimeInput(BaseModel):
    pass


class DateTimeTool(BaseTool):
    name: str = "get_current_datetime"
    description: str = "获取当前日期和时间"
    args_schema: type[BaseModel] = DateTimeInput

    def _run(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def _arun(self) -> str:
        return self._run()
