import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.tools.DateTimeTool import DateTimeTool

tool = DateTimeTool()
print(tool.name)        # get_current_datetime
print(tool.description) # 获取当前日期和时间
print(tool._run())      # 2026-07-21 11:36:54（当前时间）
