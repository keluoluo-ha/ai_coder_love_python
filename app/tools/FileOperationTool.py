from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.tools.base_tool import BaseTool


class FileOperationInput(BaseModel):
    file_operation: Literal["read", "write", "list"] = Field(description="文件操作类型")
    path: str = Field(default=".", description="工作目录内的相对路径")
    content: str | None = Field(default=None, description="写入文件的内容")


class FileOperationTool(BaseTool):
    name: str = "file_operation"
    description: str = "在受限工作目录内读取、写入或列出文件"
    parameters: type[BaseModel] = FileOperationInput

    def __init__(self, root_dir: str | Path = "."):
        self.root_dir = Path(root_dir).resolve()

    def _safe_path(self, path: str) -> Path:
        candidate = (self.root_dir / path).resolve()
        try:
            candidate.relative_to(self.root_dir)
        except ValueError as exc:
            raise ValueError("path escapes the allowed workspace") from exc
        return candidate

    async def execute(
        self,
        file_operation: Literal["read", "write", "list"],
        path: str = ".",
        content: str | None = None,
    ) -> str:
        target = self._safe_path(path)
        if file_operation == "read":
            if not target.is_file():
                raise FileNotFoundError(path)
            return target.read_text(encoding="utf-8")
        if file_operation == "list":
            if not target.is_dir():
                raise NotADirectoryError(path)
            return "\n".join(sorted(item.name for item in target.iterdir()))
        if content is None:
            raise ValueError("content is required for write")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target)
