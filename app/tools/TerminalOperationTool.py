import shlex
import subprocess
from typing import Any

from pydantic import BaseModel, Field

from app.tools.base_tool import BaseTool


class TerminalOperationInput(BaseModel):
    command: str = Field(description="需要执行的终端命令")
    timeout: int = Field(default=30, ge=1, le=120, description="超时时间，单位秒")


class TerminalOperationTool(BaseTool):
    name: str = "terminal"
    description: str = "执行受限终端命令并返回标准输出和错误"
    parameters: type[BaseModel] = TerminalOperationInput

    _blocked_tokens = {
        "rm", "rmdir", "del", "erase", "format", "shutdown", "reboot",
        "sudo", "chmod", "chown", "mkfs", "diskpart", "reg", "powershell",
    }
    _blocked_fragments = ("&&", "||", ";", "|", ">", "<", "`", "$('")

    async def execute(self, command: str, timeout: int = 30) -> str:
        if any(fragment in command for fragment in self._blocked_fragments):
            raise ValueError("command contains a blocked shell operator")
        try:
            tokens = shlex.split(command, posix=True)
        except ValueError as exc:
            raise ValueError("invalid command syntax") from exc
        if not tokens or tokens[0].lower() in self._blocked_tokens:
            raise ValueError("command is blocked")
        if any(token.lower() in self._blocked_tokens for token in tokens):
            raise ValueError("command contains a blocked token")
        try:
            completed = subprocess.run(
                tokens,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("command timed out") from exc
        output = completed.stdout.strip()
        error = completed.stderr.strip()
        return f"exit_code={completed.returncode}\nstdout={output}\nstderr={error}"
