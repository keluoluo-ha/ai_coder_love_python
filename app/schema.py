from enum import Enum, StrEnum
from pydantic import BaseModel, Field
from typing import Any, List, Literal, Optional, Union


class Role(StrEnum):
    """对话角色枚举，对齐大模型标准规范
    system: 系统提示词，设定agent规则
    user: 用户输入消息
    assistant: AI模型输出消息
    tool: 工具执行返回结果消息
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


ROLE_VALUES = tuple(role.value for role in Role)
ROLE_TYPE = Literal[ROLE_VALUES]  # type: ignore


class ToolChoice(str, Enum):
    """模型工具调用模式枚举
    none：禁止调用工具，仅纯文本对话
    auto：模型自主判断是否调用工具
    required：强制模型必须调用至少一个工具
    """
    NONE = "none"
    AUTO = "auto"
    REQUIRED = "required"


TOOL_CHOICE_VALUES = tuple(choice.value for choice in ToolChoice)
TOOL_CHOICE_TYPE = Literal[TOOL_CHOICE_VALUES]  # type: ignore


class AgentState(StrEnum):
    """智能体运行状态枚举
    IDLE：空闲待命
    RUNNING：正在执行任务
    FINISHED：任务正常结束
    ERROR：任务异常失败
    """
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
    WAITING_FOR_HUMAN="WAITING_FOR_HUMAN"

class Function(BaseModel):
    """函数调用信息结构体
    name: 工具/函数名称
    arguments: JSON字符串格式的入参
    """
    name: str
    arguments: str


class ToolCall(BaseModel):
    """消息内单次工具调用结构体，对齐OpenAI消息格式
    id: 当前工具调用唯一标识
    type: 调用类型，固定为function
    function: 具体调用的函数信息
    """
    id: str
    type: str = "function"
    function: Function


class Message(BaseModel):
    """会话单条消息模型，兼容LLM标准对话消息结构
    role: 消息角色(system/user/assistant/tool)
    content: 文本消息内容
    tool_calls: assistant发起的工具调用列表
    name: tool角色消息对应的工具名称
    tool_call_id: tool返回结果时，关联对应的工具调用id
    base64_image: 图片base64编码，用于多模态图文输入
    """
    role: ROLE_TYPE = Field(...)  # type: ignore
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)
    base64_image: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """支持运算：Message + list[Message] 、Message + Message
        方便快速拼接消息列表
        """
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持运算：list[Message] + Message
        左侧是列表，右侧是当前消息对象时触发
        """
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """将消息模型转为原生字典，用于请求LLM接口"""
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.model_dump() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        if self.base64_image is not None:
            message["base64_image"] = self.base64_image
        return message

    @classmethod
    def user_message(cls, content: str, base64_image: Optional[str] = None) -> "Message":
        return cls(role=Role.USER, content=content, base64_image=base64_image)

    
    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role=Role.SYSTEM, content=content)

    @classmethod
    def assistant_message(
        cls, content: Optional[str] = None, base64_image: Optional[str] = None
    ) -> "Message":
        """Create an assistant message"""
        return cls(role=Role.ASSISTANT, content=content, base64_image=base64_image)

    @classmethod
    def tool_message(
        cls, content: str, name, tool_call_id: str, base64_image: Optional[str] = None
    ) -> "Message":
        """Create a tool message"""
        return cls(
            role=Role.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            base64_image=base64_image,
        )

    @classmethod
    def from_tool_calls(
        cls,
        tool_calls: List[Any],
        content: Union[str, List[str]] = "",
        base64_image: Optional[str] = None,
        **kwargs,
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
            base64_image: Optional base64 encoded image
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role=Role.ASSISTANT,
            content=content,
            tool_calls=formatted_calls,
            base64_image=base64_image,
            **kwargs,
        )
class Memory(BaseModel):
    messages: List[Message] = Field(default_factory=list)
    max_messages: int = Field(default=100)

    def add_message(self, message: Message) -> None:
        """Add a message to memory"""
        self.messages.append(message)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def add_messages(self, messages: List[Message]) -> None:
        """Add multiple messages to memory"""
        self.messages.extend(messages)
        # Optional: Implement message limit
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]