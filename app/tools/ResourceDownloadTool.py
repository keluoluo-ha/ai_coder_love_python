from pathlib import Path
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field

from app.tools.base_tool import BaseTool


class ResourceDownloadInput(BaseModel):
    url: str = Field(description="需要下载的 HTTP/HTTPS 地址")
    filename: str | None = Field(default=None, description="可选输出文件名")


class ResourceDownloadTool(BaseTool):
    name: str = "resource_download"
    description: str = "下载 HTTP 或 HTTPS 资源并返回本地文件路径"
    parameters: type[BaseModel] = ResourceDownloadInput

    def __init__(self, output_dir: str | Path = "downloads"):
        self.output_dir = Path(output_dir).resolve()

    async def execute(self, url: str, filename: str | None = None) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("url must use HTTP or HTTPS")
        if filename is None:
            filename = Path(parsed.path).name or "downloaded_resource"
        if Path(filename).name != filename:
            raise ValueError("filename must be a simple filename")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / filename
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        with output_path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    output.write(chunk)
        return str(output_path)
