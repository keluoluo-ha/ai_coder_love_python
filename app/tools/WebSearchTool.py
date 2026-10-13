import requests
from pydantic import BaseModel, Field

from app.config import SEARCH_API_KEY
from app.tools.base_tool import BaseTool

SEARCH_API_URL = "https://www.searchapi.io/api/v1/search"


class WebSearchInput(BaseModel):
    query: str = Field(description="搜索关键词")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search for information from Baidu Search Engine"
    args_schema: type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        # 1. 用 requests.get 调 SearchAPI.io
        params = {
            "api_key": SEARCH_API_KEY,
            "engine": "baidu",
            "q": query,
        }
        resp = requests.get(SEARCH_API_URL, params=params)
        # 2. 解析 JSON，取 organic_results 前 5 条
        organic_list = resp.json().get("organic_results", [])[:5]
        # 3. 格式化成 "标题\n摘要\n链接" 的字符串
        chunks = []
        for item in organic_list:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            chunks.append(f"{title}\n{snippet}\n{link}")
        return "\n\n".join(chunks)

    async def _arun(self, query: str) -> str:
        return self._run(query)
