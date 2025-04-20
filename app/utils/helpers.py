import json
import os
import logging
from typing import List, Dict, Any, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_json_file(file_path: str) -> Any:
    """
    加载JSON文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        加载的JSON数据
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件失败: {str(e)}")
        return None


def save_json_file(data: Any, file_path: str) -> bool:
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        file_path: 保存路径
        
    Returns:
        是否保存成功
    """
    try:
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存JSON文件失败: {str(e)}")
        return False


def extract_document_content(documents: List[Dict[str, Any]]) -> str:
    """
    从文档列表中提取内容
    
    Args:
        documents: 文档列表
        
    Returns:
        提取的内容文本
    """
    content = []
    for doc in documents:
        if isinstance(doc, dict):
            if 'page_content' in doc:
                content.append(doc['page_content'])
            elif 'content' in doc:
                content.append(doc['content'])
            # 处理其他可能的键
            elif any(k for k in doc.keys() if 'text' in k.lower() or 'content' in k.lower()):
                for k, v in doc.items():
                    if 'text' in k.lower() or 'content' in k.lower():
                        content.append(str(v))
                        break
        elif hasattr(doc, 'page_content'):
            content.append(doc.page_content)
        else:
            content.append(str(doc))
            
    return "\n\n".join(content)


def format_chat_history(messages: List[Dict[str, str]]) -> str:
    """
    格式化聊天历史为字符串
    
    Args:
        messages: 消息列表
        
    Returns:
        格式化后的聊天历史字符串
    """
    formatted_history = []
    for message in messages:
        role = message.get("role", "")
        content = message.get("content", "")
        if role == "user":
            formatted_history.append(f"用户: {content}")
        elif role == "assistant":
            formatted_history.append(f"智能体: {content}")
        else:
            formatted_history.append(f"{role}: {content}")
    
    return "\n".join(formatted_history)


def truncate_text(text: str, max_length: int = 4000) -> str:
    """
    截断文本，确保不超过最大长度
    
    Args:
        text: 要截断的文本
        max_length: 最大长度
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    # 尝试在句子边界截断
    sentences = text.split('. ')
    result = ""
    for sentence in sentences:
        if len(result) + len(sentence) + 2 > max_length:  # +2 表示句点和空格
            break
        result += sentence + ". "
    
    # 如果无法在句子边界截断，直接截断
    if not result:
        result = text[:max_length-3] + "..."
    
    return result


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名
    
    Args:
        filename: 文件名
        
    Returns:
        文件扩展名
    """
    return os.path.splitext(filename)[1].lower() 