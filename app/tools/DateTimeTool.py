from pydantic import BaseModel
from app.tools.base_tool import BaseTool
class DateTimeInput(BaseModel):
  pass


class DateTimeTool(BaseTool):
  name:str="get_current_datetime"
  description:str="获取当前日期和时间"
  parameters:type[BaseModel]=DateTimeInput

  async def execute(self)->str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  
  