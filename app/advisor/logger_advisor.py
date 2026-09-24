import logging
import time
from collections.abc import Callable, Iterable
from typing import Any


logger = logging.getLogger("app.llm")


class LoggerAdvisor:
    """记录 LLM 调用摘要，不输出 API key 或完整消息内容。"""

    def before(self, operation: str, model: str, messages: Iterable[Any], tools: Iterable[Any] | None = None) -> float:
        tool_names = []
        for tool in tools or []:
            function = tool.get("function", {}) if isinstance(tool, dict) else {}
            if function.get("name"):
                tool_names.append(function["name"])
        logger.info(
            "llm_call_start operation=%s model=%s messages=%s tools=%s",
            operation,
            model,
            sum(1 for _ in messages),
            ",".join(tool_names) or "-",
        )
        return time.perf_counter()

    def after(self, operation: str, started_at: float, response: Any = None, error: Exception | None = None) -> None:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 1)
        if error is not None:
            logger.exception("llm_call_error operation=%s elapsed_ms=%s", operation, elapsed_ms)
            return
        content = getattr(response, "content", None)
        tool_calls = getattr(response, "tool_calls", None) or []
        if content is None and getattr(response, "choices", None):
            message = getattr(response.choices[0], "message", None)
            content = getattr(message, "content", None)
            tool_calls = getattr(message, "tool_calls", None) or []
        logger.info(
            "llm_call_end operation=%s elapsed_ms=%s content_chars=%s tool_calls=%s",
            operation,
            elapsed_ms,
            len(content or ""),
            len(tool_calls),
        )

    def around(self, operation: str, model: str, messages: Iterable[Any], tools: Iterable[Any] | None, call: Callable[[], Any]) -> Any:
        started_at = self.before(operation, model, messages, tools)
        try:
            response = call()
        except Exception as exc:
            self.after(operation, started_at, error=exc)
            raise
        self.after(operation, started_at, response)
        return response
