"""Request and response contracts shared by the API routers."""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator


class ContentBlockText(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockImage(BaseModel):
    type: Literal["image"]
    source: Dict[str, Any]


class ContentBlockImageUrl(BaseModel):
    type: Literal["image_url"]
    image_url: Dict[str, Any]


class ContentBlockToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: Dict[str, Any]


class ContentBlockToolResult(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: Union[str, List[Dict[str, Any]]]


class SystemContent(BaseModel):
    type: Literal["text"]
    text: str


class Message(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: Union[
        str,
        List[
            Union[
                ContentBlockText,
                ContentBlockImage,
                ContentBlockImageUrl,
                ContentBlockToolUse,
                ContentBlockToolResult,
            ]
        ],
    ]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class Tool(BaseModel):
    name: str
    description: Optional[str] = None
    input_schema: Dict[str, Any]


def _normalize_tools(tools: Optional[List[Any]]) -> Optional[List[Any]]:
    if not tools:
        return tools

    normalized: List[Any] = []
    for tool in tools:
        if (
            isinstance(tool, dict)
            and tool.get("type") == "function"
            and isinstance(tool.get("function"), dict)
        ):
            function = tool["function"]
            normalized.append(
                {
                    "name": function.get("name", ""),
                    "description": function.get("description"),
                    "input_schema": function.get(
                        "parameters",
                        {"type": "object", "properties": {}},
                    ),
                }
            )
        else:
            normalized.append(tool)
    return normalized


class ChatMessagesRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    max_tokens: Optional[int] = None
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    thinking: Optional[Dict[str, Any]] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None

    @field_validator("tools", mode="before")
    @classmethod
    def normalize_tools_format(cls, value: Optional[List[Any]]) -> Optional[List[Any]]:
        return _normalize_tools(value)


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


class ChatMessagesResponse(BaseModel):
    id: str
    type: Literal["message"] = "message"
    role: Literal["assistant"] = "assistant"
    model: str
    content: List[Union[ContentBlockText, ContentBlockToolUse]]
    stop_reason: Optional[
        Literal["end_turn", "max_tokens", "stop_sequence", "tool_use"]
    ] = None
    stop_sequence: Optional[str] = None
    usage: Usage


class ChatTokenCountRequest(BaseModel):
    model: str
    messages: List[Message]
    system: Optional[Union[str, List[SystemContent]]] = None
    tools: Optional[List[Tool]] = None
    thinking: Optional[Dict[str, Any]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None

    @field_validator("tools", mode="before")
    @classmethod
    def normalize_tools_format(cls, value: Optional[List[Any]]) -> Optional[List[Any]]:
        return _normalize_tools(value)


class ChatTokenCountResponse(BaseModel):
    input_tokens: int
