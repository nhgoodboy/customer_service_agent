import json
import os
import time
import logging
import functools
import asyncio
import glob
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar, cast

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义泛型类型变量
T = TypeVar('T')

def performance_monitor(func: Callable[..., T]) -> Callable[..., T]:
    """
    性能监控装饰器，记录函数执行时间和性能指标
    
    Args:
        func: 被装饰的函数
        
    Returns:
        包装后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        
        try:
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 记录执行时间
            execution_time = time.time() - start_time
            if execution_time > 1.0:  # 只记录较慢的操作
                logger.info(f"性能监控 - {func_name} 执行时间: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            # 记录异常和执行时间
            execution_time = time.time() - start_time
            logger.error(f"性能监控 - {func_name} 失败: {str(e)}, 执行时间: {execution_time:.2f}秒")
            raise  # 重新抛出异常
            
    return cast(Callable[..., T], wrapper)


def load_json_file(file_path: str) -> Optional[Any]:
    """
    加载JSON文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        解析后的JSON内容，如果失败则返回None
    """
    if not os.path.exists(file_path):
        logger.warning(f"文件不存在: {file_path}")
        return None
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件失败 {file_path}: {str(e)}")
        return None


def save_json_file(data: Any, file_path: str) -> bool:
    """
    保存内容到JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
        
    Returns:
        是否成功保存
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"已保存数据到文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存数据到文件失败 {file_path}: {str(e)}")
        return False


def extract_document_content(document: Dict[str, Any]) -> str:
    """
    从文档字典中提取内容
    
    Args:
        document: 文档字典
        
    Returns:
        提取的内容
    """
    # 如果文档是字典，尝试提取内容字段
    if "content" in document:
        return document["content"]
    elif "text" in document:
        return document["text"]
    elif "page_content" in document:
        return document["page_content"]
    
    # 如果没有找到内容字段，将整个文档转换为字符串
    try:
        return json.dumps(document, ensure_ascii=False)
    except:
        return str(document)


def truncate_text(text: str, max_length: int = 2000) -> str:
    """
    截断文本，避免超过最大长度
    
    Args:
        text: 要截断的文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    # 截断文本
    return text[:max_length] + "..."


def format_chat_history(chat_history: List[Dict[str, str]], max_messages: int = 10) -> str:
    """
    格式化聊天历史记录
    
    Args:
        chat_history: 聊天历史记录
        max_messages: 最大消息数量
        
    Returns:
        格式化后的聊天历史
    """
    # 限制消息数量
    if len(chat_history) > max_messages:
        chat_history = chat_history[-max_messages:]
    
    # 格式化消息
    formatted_history = []
    for message in chat_history:
        role = message.get("role", "")
        content = message.get("content", "")
        
        if role == "user":
            formatted_history.append(f"用户: {content}")
        elif role == "assistant":
            formatted_history.append(f"助手: {content}")
    
    return "\n".join(formatted_history)


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        文件扩展名
    """
    return os.path.splitext(filename)[1].lower()


def find_files_by_pattern(directory: str, pattern: str) -> List[str]:
    """
    根据模式查找目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件模式（如 *.json）
        
    Returns:
        匹配的文件路径列表
    """
    if not os.path.exists(directory):
        logger.warning(f"目录不存在: {directory}")
        return []
        
    try:
        # 使用glob查找匹配文件
        file_pattern = os.path.join(directory, pattern)
        files = glob.glob(file_pattern)
        
        # 按文件名排序，确保结果稳定
        files.sort()
        
        if not files:
            logger.info(f"目录 {directory} 中没有匹配 {pattern} 的文件")
            
        return files
        
    except Exception as e:
        logger.error(f"查找文件时发生错误: {str(e)}")
        return []


def format_response(message: str, status: str = "success", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    格式化响应数据
    
    Args:
        message: 响应消息
        status: 状态
        data: 响应数据
        
    Returns:
        格式化的响应字典
    """
    response = {
        "status": status,
        "message": message
    }
    
    if data:
        response["data"] = data
        
    return response 