from app.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
import requests
from app.config import SEARCH_API_KEY

SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"


class WebSearchInput(BaseModel):
  query:str=Field(description="搜索关键词")

class WebSearchTool(BaseTool):
  name:str="web_search"
  description:str="Search for information from Baidu Search Engine"
  parameters: type[BaseModel] = WebSearchInput


  async def execute(self,query:str)->str:
    # 1. 用 requests.get 调 SearchAPI.io
    params = {
    "api_key": SEARCH_API_KEY,
    "engine": "baidu",
    "q": query
    }
    resp = requests.get(SEARCH_API_URL, params=params)
    # 2. 解析 JSON，取 organic_results 前 5 条
    data = resp.json()
    organic_list = data.get("organic_results", [])[:5]
    # 3. 格式化成 "标题\n摘要\n链接" 的字符串
    chunks = []
    for item in organic_list:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            # 严格格式：标题\n摘要\n链接
            chunks.append(f"{title}\n{snippet}\n{link}")

        # 多条之间用换行分隔
    return "\n\n".join(chunks)
