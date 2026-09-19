from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup

from app.tools.base_tool import BaseTool


class WebScrapingInput(BaseModel):
    url: str = Field(description="需要抓取的 HTTP 或 HTTPS 页面")


class WebScrapingTool(BaseTool):
    name: str = "web_scraping"
    description: str = "抓取网页正文并去除脚本、样式和页面导航噪声"
    parameters: type[BaseModel] = WebScrapingInput

    async def execute(self, url: str) -> str:
        response = requests.get(
            url,
            timeout=30,
            headers={"User-Agent": "ai-agent-love/1.0"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            element.decompose()
        root = soup.find("article") or soup.find("main") or soup.body or soup
        lines = [line.strip() for line in root.get_text("\n").splitlines()]
        return "\n".join(line for line in lines if line)
