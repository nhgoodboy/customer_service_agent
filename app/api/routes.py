from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, List, Any, Optional
import uuid
import logging

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    IntentType,
    DocumentInput
)
from app.services.chat_service import chat_service
from app.services.knowledge_service import knowledge_service
from app.core.session_manager import session_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口
    
    Args:
        request: 聊天请求
        
    Returns:
        聊天响应
    """
    # 参数验证
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=422, detail="查询内容不能为空")
    
    # 确保有session_id
    if not request.session_id:
        request.session_id = str(uuid.uuid4())
    
    try:
        return await chat_service.process_chat(request)
    except Exception as e:
        logger.error(f"聊天处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.post("/session/create", response_model=Dict[str, str])
async def create_session():
    """
    创建新会话
    
    Returns:
        包含会话ID的字典
    """
    session_id = session_manager.create_session()
    return {"session_id": session_id}


@router.get("/session/create", response_model=Dict[str, str])
async def create_session_get():
    """
    创建新会话(GET方法)，兼容前端
    
    Returns:
        包含会话ID的字典
    """
    session_id = session_manager.create_session()
    return {"session_id": session_id}


@router.get("/session/{session_id}/history", response_model=List[Dict[str, str]])
async def get_chat_history(session_id: str):
    """
    获取会话历史
    
    Args:
        session_id: 会话ID
        
    Returns:
        聊天历史记录
    """
    history = session_manager.get_chat_history(session_id)
    return history


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    清除会话历史
    
    Args:
        session_id: 会话ID
        
    Returns:
        操作结果
    """
    success = session_manager.clear_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话历史已清除"}


@router.post("/knowledge/init", response_model=Dict[str, Any])
async def init_knowledge_base():
    """
    初始化知识库
    
    Returns:
        初始化结果
    """
    results = knowledge_service.init_knowledge_base()
    return {"success": True, "results": results}


@router.post("/knowledge/add", response_model=Dict[str, Any])
async def add_knowledge(
    document: DocumentInput,
    intent_type: IntentType = Body(..., description="意图类型")
):
    """
    添加知识到知识库
    
    Args:
        document: 文档内容
        intent_type: 意图类型
        
    Returns:
        添加结果
    """
    success = knowledge_service.add_document(document, intent_type)
    return {"success": success}


@router.post("/knowledge/clear", response_model=Dict[str, Any])
async def clear_knowledge_base(
    intent_type: Optional[IntentType] = Body(None, description="意图类型，不提供则清空所有")
):
    """
    清空知识库
    
    Args:
        intent_type: 意图类型，不提供则清空所有
        
    Returns:
        清空结果
    """
    results = knowledge_service.clear_knowledge_base(intent_type)
    return {"success": True, "results": results}


@router.get("/knowledge/files", response_model=List[str])
async def get_knowledge_files():
    """
    获取所有知识文件
    
    Returns:
        知识文件路径列表
    """
    files = knowledge_service.get_all_knowledge_files()
    return files


@router.get("/knowledge/file/{file_name}", response_model=Any)
async def get_knowledge_file_content(file_name: str):
    """
    获取知识文件内容
    
    Args:
        file_name: 文件名
        
    Returns:
        文件内容
    """
    content = knowledge_service.get_knowledge_content(file_name)
    if content is None:
        raise HTTPException(status_code=404, detail="文件不存在或无法读取")
    return content


@router.get("/health")
async def health_check():
    """
    健康检查接口
    
    Returns:
        服务状态
    """
    return {"status": "ok"}


@router.get("/session/{session_id}/context", response_model=Dict[str, Any])
async def get_session_context(session_id: str):
    """
    获取会话上下文信息
    
    Args:
        session_id: 会话ID
        
    Returns:
        会话上下文信息
    """
    context = session_manager.get_session_context(session_id)
    return context 