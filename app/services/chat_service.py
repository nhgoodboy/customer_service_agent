import logging
from typing import Dict, List, Any, Optional
import json
import re

from app.models.schemas import IntentType, ChatRequest, ChatResponse
from app.core.llm_manager import llm_manager
from app.core.intent_classifier import intent_classifier
from app.core.rag_retriever import rag_retriever
from app.core.session_manager import session_manager
from app.utils.helpers import extract_document_content, truncate_text, format_chat_history
from config.settings import KNOWLEDGE_BASE_PATH
from app.services.knowledge_service import knowledge_service
import os

logger = logging.getLogger(__name__)


class ChatService:
    """聊天服务，整合意图识别、RAG检索和会话管理"""
    
    def __init__(self):
        """初始化聊天服务"""
        self.llm_manager = llm_manager
        self.intent_classifier = intent_classifier
        self.rag_retriever = rag_retriever
        self.session_manager = session_manager
    
    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        处理聊天请求
        
        Args:
            request: 聊天请求
            
        Returns:
            聊天响应
        """
        query = request.query
        session_id = request.session_id
        
        try:
            # 保存用户消息到会话历史
            self.session_manager.add_message(session_id, "user", query)
            
            # 获取聊天历史
            chat_history = self.session_manager.get_chat_history(session_id)
            
            # 分类意图
            intent_result = await self.intent_classifier.classify(query)
            intent = intent_result.intent
            
            # 记录意图到会话元数据
            self.session_manager.set_session_metadata(session_id, "last_intent", intent.value)
            
            # 提取订单号
            order_id = self._extract_order_id(query)
            
            # 如果意图是订单查询且找到了订单号，优先使用直接订单查询
            if intent == IntentType.ORDER_STATUS and order_id:
                order_info = self._find_order_by_id(order_id)
                if order_info:
                    # 如果找到了订单信息，直接生成回复
                    response_text = await self._generate_order_response(order_id, order_info, query)
                    
                    # 保存助手回复到会话历史
                    self.session_manager.add_message(session_id, "assistant", response_text)
                    
                    # 创建响应
                    response = ChatResponse(
                        response=response_text,
                        intent=intent,
                        sources=["order_samples.json"]
                    )
                    
                    return response
            
            # 如果不是订单查询或没有找到订单，使用常规RAG检索
            rag_result = await self.rag_retriever.retrieve(query, intent)
            
            # 生成回复
            response_text = await self._generate_response(query, intent, rag_result, chat_history)
            
            # 保存助手回复到会话历史
            self.session_manager.add_message(session_id, "assistant", response_text)
            
            # 创建响应
            response = ChatResponse(
                response=response_text,
                intent=intent,
                sources=rag_result.sources if rag_result.documents else None
            )
            
            return response
            
        except Exception as e:
            logger.error(f"处理聊天请求失败: {str(e)}")
            
            # 保存错误响应到会话历史
            error_message = "抱歉，我在处理您的请求时遇到了问题，请稍后再试。"
            self.session_manager.add_message(session_id, "assistant", error_message)
            
            return ChatResponse(
                response=error_message,
                intent=IntentType.UNKNOWN
            )
    
    def _extract_order_id(self, query: str) -> Optional[str]:
        """
        从查询中提取订单号
        
        Args:
            query: 用户查询
            
        Returns:
            订单号或None
        """
        # 常见的订单号格式，例如OD+年月日+数字
        pattern = r'OD\d{10,12}'
        match = re.search(pattern, query)
        if match:
            return match.group(0)
        return None
    
    def _find_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        根据订单号查找订单信息
        
        Args:
            order_id: 订单号
            
        Returns:
            订单信息或None
        """
        # 使用知识服务查找订单
        order_info = knowledge_service.find_order_by_id(order_id)
        if order_info:
            return order_info
            
        # 如果知识服务未找到，尝试直接从文件查找
        order_files = ["order_samples.json"]
        for file_name in order_files:
            file_path = os.path.join(KNOWLEDGE_BASE_PATH, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        orders = json.load(f)
                        
                    # 搜索订单号
                    if isinstance(orders, list):
                        for order in orders:
                            if isinstance(order, dict) and order.get("order_id") == order_id:
                                logger.info(f"在文件 {file_name} 中找到订单 {order_id}")
                                return order
                except Exception as e:
                    logger.error(f"读取订单文件 {file_path} 失败: {str(e)}")
        
        logger.warning(f"未找到订单号 {order_id} 的信息")
        return None
    
    async def _generate_order_response(self, order_id: str, order_info: Dict[str, Any], query: str) -> str:
        """
        生成订单查询回复
        
        Args:
            order_id: 订单号
            order_info: 订单信息
            query: 用户查询
            
        Returns:
            生成的回复
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # 将订单信息转换为格式化文本
        order_text = json.dumps(order_info, ensure_ascii=False, indent=2)
        
        # 系统提示
        system_prompt = """你是一个专业的电商客服助手，擅长处理订单状态查询。
请根据提供的订单信息回答用户关于订单的问题。准确说明订单的状态、物流信息和预计送达时间。
回答要基于提供的订单数据，语言要自然友好，不要直接返回JSON数据。
回答时保持友好、专业的语气，确保回答简洁明了。"""
        
        # 用户提示
        user_prompt = f"""订单信息:
{order_text}

用户问题:
{query}

请基于以上订单信息回答用户问题:"""
        
        # 调用LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await self.llm_manager.llm.ainvoke(messages)
            if hasattr(response, 'content'):
                return response.content
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except Exception as e:
            logger.error(f"生成订单回复失败: {str(e)}")
            return f"根据订单号 {order_id} 查询到相关信息，但在处理过程中遇到问题。请稍后再试。"
    
    async def _generate_response(
        self, 
        query: str, 
        intent: IntentType, 
        rag_result: Any, 
        chat_history: List[Dict[str, str]]
    ) -> str:
        """
        生成回复
        
        Args:
            query: 用户查询
            intent: 意图
            rag_result: RAG检索结果
            chat_history: 聊天历史
            
        Returns:
            生成的回复
        """
        try:
            # 确定系统提示
            system_prompt = self._get_system_prompt_by_intent(intent)
            
            # 提取检索文档内容
            context = ""
            if rag_result.documents:
                # 将文档转换为文本
                docs_text = []
                for doc in rag_result.documents:
                    if isinstance(doc, dict):
                        docs_text.append(json.dumps(doc, ensure_ascii=False))
                    else:
                        docs_text.append(str(doc))
                
                context = "\n\n".join(docs_text)
                
                # 截断文本以避免超过最大长度
                context = truncate_text(context, max_length=3000)
            
            # 如果没有检索到文档，使用通用回复
            if not context:
                # 直接使用LLM回答，使用相同的消息格式
                from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
                
                # 创建系统消息和用户消息
                messages = [
                    SystemMessage(content=system_prompt)
                ]
                
                # 添加历史消息（如果有的话）
                for msg in chat_history[:-1]:  # 排除最后一条用户消息
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
                
                # 添加当前用户查询
                messages.append(HumanMessage(content=query))
                
                try:
                    # 调用LLM
                    response = await self.llm_manager.llm.ainvoke(messages)
                    if hasattr(response, 'content'):
                        return response.content
                    elif isinstance(response, str):
                        return response
                    else:
                        # 处理其他可能的响应格式
                        return str(response)
                except Exception as e:
                    logger.error(f"调用LLM失败: {str(e)}")
                    # 使用直接查询作为备选方案
                    return self.llm_manager.direct_query(query, system_prompt)
            
            # 使用RAG提示模板
            rag_prompt = f"""
{system_prompt}

检索到的信息:
{context}

用户问题:
{query}

请基于检索到的信息回答用户问题:
"""
            
            # 直接调用LLM
            from langchain_core.messages import SystemMessage, HumanMessage
            messages = [SystemMessage(content=rag_prompt)]
            try:
                response = await self.llm_manager.llm.ainvoke(messages)
                if hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                else:
                    # 处理其他可能的响应格式
                    return str(response)
            except Exception as e:
                logger.error(f"调用RAG LLM失败: {str(e)}")
                # 使用直接查询作为备选方案
                return self.llm_manager.direct_query(rag_prompt)
            
        except Exception as e:
            logger.error(f"生成回复失败: {str(e)}")
            return "抱歉，我暂时无法回答您的问题，请稍后再试。"
    
    def _get_system_prompt_by_intent(self, intent: IntentType) -> str:
        """
        根据意图获取系统提示
        
        Args:
            intent: 用户意图
            
        Returns:
            系统提示
        """
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
回答时保持友好、专业的语气，确保回答简洁明了。""",
            
            IntentType.UNKNOWN: """你是一个专业的电商客服助手，负责回答用户的各类问题。
请根据提供的信息回答用户的问题。如果无法确定用户的具体意图，请尝试提供有用的一般性信息。
如果检索信息中没有相关内容，请坦率承认不知道，不要编造信息。
回答时保持友好、专业的语气，确保回答简洁明了。"""
        }
        
        return prompts.get(intent, prompts[IntentType.UNKNOWN])


# 单例模式
chat_service = ChatService() 