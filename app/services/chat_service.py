import logging
from typing import Dict, List, Any, Optional
import json

from app.models.schemas import IntentType, ChatRequest, ChatResponse
from app.core.llm_manager import llm_manager
from app.core.intent_classifier import intent_classifier
from app.core.rag_retriever import rag_retriever
from app.core.session_manager import session_manager
from app.utils.helpers import extract_document_content, truncate_text, format_chat_history

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
            
            # 检索相关文档
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
                # 直接使用LLM回答
                formatted_history = self.llm_manager.format_chat_history(chat_history[:-1])  # 排除最后一条用户消息
                
                prompt = f"用户查询: {query}"
                
                # 创建聊天链并调用
                chat_chain = self.llm_manager.get_chat_chain(system_prompt)
                response = await chat_chain.ainvoke({
                    "messages": formatted_history + [{"role": "user", "content": prompt}]
                })
                
                return response
            
            # 使用RAG链生成回复
            rag_chain = self.llm_manager.get_rag_chain(system_prompt)
            
            # 添加历史上下文到提示中
            if len(chat_history) > 1:
                history_text = format_chat_history(chat_history[:-1])  # 排除最后一条用户消息
                user_query = f"聊天历史:\n{history_text}\n\n当前问题: {query}"
            else:
                user_query = query
            
            # 调用RAG链
            response = await rag_chain.ainvoke({
                "context": context,
                "query": user_query
            })
            
            return response
            
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