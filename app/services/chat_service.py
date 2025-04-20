import json
import logging
import os
import re
import uuid
from datetime import datetime
import time
import traceback
from typing import Dict, List, Optional, Any, Tuple

from app.models.schemas import IntentType, ChatRequest, ChatResponse
from app.core.intent_classifier import intent_classifier
from app.core.rag_retriever import rag_retriever
from app.core.llm_manager import llm_manager
from app.utils.helpers import performance_monitor
from config.settings import KNOWLEDGE_BASE_PATH
from app.services.knowledge_service import knowledge_service

# 配置日志
logger = logging.getLogger(__name__)

class ChatService:
    """聊天服务，处理聊天会话和消息"""
    
    def __init__(self):
        """初始化聊天服务"""
        self.sessions = {}
        logger.info("聊天服务初始化完成")
    
    def create_session(self) -> Dict[str, Any]:
        """创建新的聊天会话"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "history": []
        }
        logger.info(f"创建新会话: {session_id}")
        return {"id": session_id}
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取指定会话"""
        session = self.sessions.get(session_id)
        if not session:
            logger.warning(f"会话未找到: {session_id}")
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """删除指定会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"会话已删除: {session_id}")
            return True
        logger.warning(f"尝试删除不存在的会话: {session_id}")
        return False
    
    @performance_monitor
    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """处理聊天请求"""
        try:
            # 获取或创建会话
            session_id = request.session_id
            session = self.get_session(session_id)
            if not session:
                session_info = self.create_session()
                session_id = session_info["id"]
                session = self.get_session(session_id)
            
            query = request.query
            logger.info(f"处理聊天请求: 会话={session_id}, 查询='{query}'")
            
            # 将用户消息添加到历史记录
            session["history"].append({
                "role": "user",
                "content": query,
                "timestamp": datetime.now().isoformat()
            })
            
            # 提取订单ID
            order_id = self._extract_order_id(query)
            
            # 意图分类
            intent_result = await intent_classifier.classify(query)
            intent = intent_result.intent
            confidence = intent_result.confidence
            
            logger.info(f"意图分类: {intent}, 置信度: {confidence}")
            
            # 如果是订单查询
            if intent == IntentType.ORDER_STATUS and order_id:
                logger.info(f"检测到订单查询: {order_id}")
                order_info = self._find_order_by_id(order_id)
                
                if order_info:
                    # 生成订单响应
                    response_text = self._generate_order_response(order_info)
                    
                    # 添加响应到历史记录
                    session["history"].append({
                        "role": "assistant",
                        "content": response_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 返回响应
                    return ChatResponse(
                        response=response_text,
                        intent=intent,
                        sources=[]
                    )
            
            # 使用RAG检索相关文档
            rag_result = await rag_retriever.retrieve(query, intent)
            
            # 生成响应
            response_text = await self._generate_response(
                query=query,
                intent=intent,
                docs=rag_result.documents,
                history=session["history"],
                system_prompt=request.system_prompt
            )
            
            # 添加响应到历史记录
            session["history"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # 创建响应对象
            response = ChatResponse(
                response=response_text,
                intent=intent,
                sources=rag_result.sources if rag_result.sources else []
            )
            
            return response
            
        except Exception as e:
            logger.error(f"处理聊天请求时出错: {str(e)}")
            traceback.print_exc()
            
            # 返回错误响应
            return ChatResponse(
                response="抱歉，处理您的请求时出现了问题。请稍后再试。",
                intent=IntentType.UNKNOWN,
                sources=[]
            )
    
    def _extract_order_id(self, query: str) -> Optional[str]:
        """从查询中提取订单ID"""
        pattern = r'OD\d{10,13}'  # 允许更长的订单号
        match = re.search(pattern, query)
        if match:
            order_id = match.group()
            logger.info(f"从查询中提取到订单ID: {order_id}")
            return order_id
        return None
    
    def _find_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """根据订单ID查找订单信息"""
        try:
            # 使用知识服务查找订单
            order = knowledge_service.find_order_by_id(order_id)
            if order:
                logger.info(f"通过知识服务找到订单: {order_id}")
                return order
            
            # 如果知识服务未找到，直接从文件读取
            file_path = os.path.join(KNOWLEDGE_BASE_PATH, "order_samples.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    orders = json.load(f)
                
                # 搜索订单
                for order in orders:
                    if order.get("order_id") == order_id:
                        logger.info(f"直接从文件找到订单: {order_id}")
                        return order
            
            logger.warning(f"未找到订单: {order_id}")
            return None
        except Exception as e:
            logger.error(f"查找订单时出错: {str(e)}")
            return None
    
    def _generate_order_response(self, order_info: Dict[str, Any]) -> str:
        """根据订单信息生成响应"""
        try:
            order_id = order_info.get("order_id", "未知")
            status = order_info.get("status", "未知").lower()
            
            # 根据不同的订单状态生成不同的响应
            status_messages = {
                "shipped": f"您的订单 {order_id} 已发货，正在配送中。",
                "delivered": f"您的订单 {order_id} 已送达。",
                "processing": f"您的订单 {order_id} 正在处理中，我们会尽快安排发货。",
                "cancelled": f"您的订单 {order_id} 已取消。",
                "pending": f"您的订单 {order_id} 正在等待确认。"
            }
            
            response = status_messages.get(status, f"您的订单 {order_id} 状态为: {status}")
            
            # 添加预计送达时间
            if "estimated_delivery" in order_info:
                response += f" 预计送达时间为 {order_info['estimated_delivery']}。"
            
            # 添加物流信息
            if "tracking_number" in order_info:
                tracking = order_info["tracking_number"]
                carrier = order_info.get("carrier", "物流公司")
                response += f" 物流公司: {carrier}, 物流单号: {tracking}。"
            
            # 添加友好结尾
            response += "如果您有其他问题，随时告诉我。"
            
            return response
        except Exception as e:
            logger.error(f"生成订单响应时出错: {str(e)}")
            return f"抱歉，我在处理您关于订单 {order_info.get('order_id', '未知')} 的查询时遇到了问题。请稍后再试。"
    
    async def _generate_response(self, query: str, intent: IntentType, docs: List[Any], history: List[Dict[str, Any]], system_prompt: Optional[str] = None) -> str:
        """生成聊天响应"""
        try:
            if not docs:
                logger.info("未找到相关文档，使用通用回复模板")
                
                # 根据意图提供通用回复
                if intent == IntentType.PRODUCT_INQUIRY:
                    return "抱歉，我没有找到与您询问的产品相关的信息。请提供更多细节，例如产品名称或型号。"
                elif intent == IntentType.ORDER_STATUS:
                    return "抱歉，我无法找到您的订单信息。请确认您提供的订单号是否正确。"
                elif intent == IntentType.RETURN_REFUND:
                    return "关于退货和退款的问题，请提供您的订单号和想要退货的商品，以便我为您提供更准确的帮助。"
                else:
                    return "抱歉，我无法理解您的问题。请尝试用不同的方式提问，或提供更多信息。"
            
            # 使用LLM生成响应
            if not system_prompt:
                system_prompt = self._get_system_prompt(intent)
                
            # 处理不同格式的文档内容
            doc_contents = []
            for doc in docs:
                if isinstance(doc, dict):
                    # 如果是字典，尝试提取内容
                    if "content" in doc:
                        doc_contents.append(str(doc["content"]))
                    else:
                        # 如果没有content字段，将整个字典转为字符串
                        doc_contents.append(json.dumps(doc, ensure_ascii=False))
                else:
                    # 如果是Document对象
                    if hasattr(doc, "page_content"):
                        doc_contents.append(doc.page_content)
                    else:
                        # 其他情况，转为字符串
                        doc_contents.append(str(doc))
            
            # 合并文档内容
            context = "\n\n".join(doc_contents)
            
            # 构建消息列表
            messages = []
            
            # 添加系统提示
            messages.append({"role": "system", "content": system_prompt})
                
            # 添加上下文
            if context:
                messages.append({"role": "system", "content": f"参考信息:\n{context}"})
                
            # 添加聊天历史
            for msg in history[-6:-1]:  # 仅使用最近5条消息（不包括当前查询）
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 添加当前查询
            messages.append({"role": "user", "content": query})
            
            # 生成响应
            response = await llm_manager.generate_response(messages)
            
            return response
            
        except Exception as e:
            logger.error(f"生成响应时出错: {str(e)}")
            return "抱歉，我暂时无法回答您的问题。请稍后再试。"
    
    def _get_system_prompt(self, intent: IntentType) -> str:
        """根据意图获取系统提示词"""
        prompts = {
            IntentType.PRODUCT_INQUIRY: """你是一个专业的电商客服助手，擅长回答商品相关问题。
请根据提供的信息回答用户的商品咨询。回答要详细、准确，突出商品的优势和特点。
如果检索信息中没有相关内容，请坦率承认不知道，不要编造信息。
回答时保持友好、专业的语气，确保回答简洁明了。""",
            
            IntentType.ORDER_STATUS: """你是一个专业的电商客服助手，擅长处理订单状态查询。
请根据提供的信息回答用户关于订单的问题。准确说明订单的状态、物流信息和预计送达时间。
如果需要更多信息（如订单号），请礼貌地向用户询问。
如果检索信息中没有相关内容，请坦率承认不知道，不要编造信息。
回答时保持友好、专业的语气，确保回答简洁明了。""",
            
            IntentType.RETURN_REFUND: """你是一个专业的电商客服助手，擅长处理退货退款问题。
请根据提供的信息回答用户关于退货、退款的问题。清晰说明退货退款政策、流程和注意事项。
如果需要更多信息（如订单号、退货原因），请礼貌地向用户询问。
如果检索信息中没有相关内容，请坦率承认不知道，不要编造信息。
回答时保持友好、专业的语气，确保回答简洁明了。""",
            
            IntentType.GENERAL_INQUIRY: """你是一个专业的电商客服助手，擅长回答各类一般性问题。
请根据提供的信息回答用户的问题。提供全面、准确的解答。
如果检索信息中没有相关内容，请坦率承认不知道，不要编造信息。
回答时保持友好、专业的语气，确保回答简洁明了。"""
        }
        
        return prompts.get(intent, prompts[IntentType.GENERAL_INQUIRY])

# 创建聊天服务实例
chat_service = ChatService() 