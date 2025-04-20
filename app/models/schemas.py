from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum


class IntentType(str, Enum):
    """意图类型枚举"""
    PRODUCT_INQUIRY = "product_inquiry"
    ORDER_STATUS = "order_status"
    RETURN_REFUND = "return_refund"
    GENERAL_INQUIRY = "general_inquiry"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """消息模型"""
    role: str
    content: str


class ChatHistory(BaseModel):
    """聊天历史模型"""
    messages: List[Message] = []


class IntentClassificationResponse(BaseModel):
    """意图分类响应模型"""
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    message: Optional[str] = None


class RAGResult(BaseModel):
    """RAG检索结果模型"""
    documents: List[Dict[str, Any]]
    sources: List[str]
    query: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    query: str
    session_id: str
    system_prompt: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    intent: Optional[IntentType] = None
    sources: Optional[List[str]] = None


class DocumentInput(BaseModel):
    """知识库文档输入模型"""
    text: str
    metadata: Dict[str, Any]
    id: Optional[str] = None 