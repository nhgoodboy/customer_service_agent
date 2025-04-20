import logging
from typing import Dict, List, Any, Optional
import uuid
import time

from app.models.schemas import Message, ChatHistory

logger = logging.getLogger(__name__)


class SessionManager:
    """会话管理器，负责管理用户的对话会话"""
    
    def __init__(self, session_ttl: int = 3600 * 24):
        """
        初始化会话管理器
        
        Args:
            session_ttl: 会话过期时间（秒），默认24小时
        """
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_ttl = session_ttl
    
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话数据字典
        """
        # 检查会话ID是否有效
        if not session_id or session_id == "undefined" or not isinstance(session_id, str):
            logger.warning(f"无效的会话ID: {session_id}，创建新的会话ID")
            session_id = str(uuid.uuid4())
        
        # 如果会话不存在，创建新会话
        if session_id not in self.sessions:
            logger.info(f"创建新会话: {session_id}")
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": time.time(),
                "last_active": time.time(),
                "history": ChatHistory(messages=[])
            }
        else:
            # 更新活跃时间
            self.sessions[session_id]["last_active"] = time.time()
        
        # 清理过期会话
        self._cleanup_expired_sessions()
        
        return self.sessions[session_id]
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        向会话添加消息
        
        Args:
            session_id: 会话ID
            role: 消息角色（user或assistant）
            content: 消息内容
        """
        session = self.get_session(session_id)
        session["history"].messages.append(Message(role=role, content=content))
        session["last_active"] = time.time()
    
    def get_chat_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        获取聊天历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            聊天历史记录列表
        """
        session = self.get_session(session_id)
        
        # 将消息转换为字典格式
        history = []
        for message in session["history"].messages:
            history.append({
                "role": message.role,
                "content": message.content
            })
        
        return history
    
    def clear_session(self, session_id: str) -> bool:
        """
        清除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功清除
        """
        if session_id in self.sessions:
            # 保留会话但清除历史记录
            self.sessions[session_id]["history"] = ChatHistory(messages=[])
            self.sessions[session_id]["last_active"] = time.time()
            logger.info(f"已清除会话历史: {session_id}")
            return True
        
        logger.warning(f"尝试清除不存在的会话: {session_id}")
        return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功删除
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"已删除会话: {session_id}")
            return True
        
        logger.warning(f"尝试删除不存在的会话: {session_id}")
        return False
    
    def create_session(self) -> str:
        """
        创建新会话
        
        Returns:
            新会话ID
        """
        session_id = str(uuid.uuid4())
        self.get_session(session_id)  # 初始化会话
        return session_id
    
    def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话上下文数据
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话上下文信息
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return {
                    "exists": False,
                    "message": "会话不存在"
                }
            
            # 计算消息数量
            message_count = len(session.get("messages", []))
            
            # 返回会话上下文信息
            return {
                "exists": True,
                "session_id": session_id,
                "created_at": session.get("created_at"),
                "last_active": session.get("last_active"),
                "message_count": message_count,
                "expires_at": session.get("last_active", 0) + self.session_ttl
            }
        except Exception as e:
            logging.error(f"获取会话上下文失败: {str(e)}")
            return {
                "exists": False,
                "message": f"获取会话上下文失败: {str(e)}"
            }
    
    def _cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session["last_active"] > self.session_ttl:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            logger.info(f"清理过期会话: {session_id}")
            del self.sessions[session_id]
    
    def set_session_metadata(self, session_id: str, key: str, value: Any) -> None:
        """
        设置会话元数据
        
        Args:
            session_id: 会话ID
            key: 元数据键
            value: 元数据值
        """
        session = self.get_session(session_id)
        
        if "metadata" not in session:
            session["metadata"] = {}
        
        session["metadata"][key] = value
    
    def get_session_metadata(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        获取会话元数据
        
        Args:
            session_id: 会话ID
            key: 元数据键
            default: 默认值
            
        Returns:
            元数据值
        """
        session = self.get_session(session_id)
        
        if "metadata" not in session:
            return default
        
        return session["metadata"].get(key, default)


# 单例模式
session_manager = SessionManager() 