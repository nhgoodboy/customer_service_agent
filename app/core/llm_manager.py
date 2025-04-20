import os
from typing import List, Dict, Any, Optional, Union
import logging

from langchain.prompts import PromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_deepseek import ChatDeepSeek

from config.settings import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, TEMPERATURE, MAX_TOKENS

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM管理器，负责管理和调用DeepSeek LLM"""
    
    def __init__(self):
        """初始化LLM管理器"""
        self._llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """初始化LLM"""
        if not DEEPSEEK_API_KEY:
            logger.error("未设置DeepSeek API密钥，请在.env文件中设置DEEPSEEK_API_KEY")
            raise ValueError("未设置DeepSeek API密钥")
        
        try:
            self._llm = ChatDeepSeek(
                model=DEEPSEEK_MODEL,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                model_kwargs={"deepseek_api_key": DEEPSEEK_API_KEY}  # 新方式
            )
            logger.info(f"成功初始化DeepSeek LLM: {DEEPSEEK_MODEL}")
        except Exception as e:
            logger.error(f"初始化DeepSeek LLM失败: {str(e)}")
            raise
    
    @property
    def llm(self) -> BaseChatModel:
        """获取LLM实例"""
        if self._llm is None:
            self._initialize_llm()
        return self._llm
    
    def get_chat_chain(self, system_prompt: str = None):
        """
        获取聊天链
        
        Args:
            system_prompt: 系统提示，如果不提供则使用默认值
            
        Returns:
            聊天链
        """
        if system_prompt is None:
            system_prompt = "你是一个专业的电商客服助手，负责回答用户关于商品、订单、退款等问题。请提供准确、有用的信息，并保持友好的态度。"
        
        chat_chain = (
            RunnablePassthrough.assign(
                messages=lambda x: [
                    SystemMessage(content=system_prompt),
                    *x["messages"]
                ]
            )
            | self.llm
            | StrOutputParser()
        )
        
        return chat_chain
    
    def get_intent_classification_chain(self):
        """
        获取意图分类链
        
        Returns:
            意图分类链
        """
        intent_system_prompt = """你是一个专业的意图分类助手。你的任务是分析用户的查询并将其分类为以下意图类别之一：
- product_inquiry: 与商品相关的咨询，如商品功能、规格、库存等
- order_status: 与订单状态相关的查询，如订单跟踪、发货状态等
- return_refund: 与退货退款相关的查询，如退货流程、退款状态等
- general_inquiry: 其他一般性问题，如账户问题、平台政策等

仅返回最匹配的意图类别名称，不要返回任何其他内容。
"""
        
        intent_classification_chain = (
            RunnablePassthrough.assign(
                messages=lambda x: [
                    SystemMessage(content=intent_system_prompt),
                    HumanMessage(content=x["query"])
                ]
            )
            | self.llm
            | StrOutputParser()
        )
        
        return intent_classification_chain
    
    def get_rag_chain(self, system_prompt: str = None):
        """
        获取RAG链
        
        Args:
            system_prompt: 系统提示，如果不提供则使用默认值
            
        Returns:
            RAG链
        """
        if system_prompt is None:
            system_prompt = """你是一个专业的电商客服助手。请根据以下检索到的信息来回答用户的问题。
如果检索信息中没有相关内容，请坦率承认你不知道，不要编造信息。
回答时请保持友好、专业的语气，并确保回答简洁明了。
"""
        
        rag_prompt = PromptTemplate.from_template(
            """
{system_prompt}

检索到的信息:
{context}

用户问题:
{query}

请基于检索到的信息回答用户问题:
"""
        )
        
        rag_chain = (
            RunnablePassthrough.assign(
                system_prompt=lambda _: system_prompt,
            )
            | rag_prompt
            | self.llm
            | StrOutputParser()
        )
        
        return rag_chain
    
    def direct_query(self, query: str, system_prompt: str = None) -> str:
        """
        直接查询LLM
        
        Args:
            query: 查询文本
            system_prompt: 系统提示
            
        Returns:
            LLM响应
        """
        if system_prompt is None:
            system_prompt = "你是一个专业的电商客服助手，负责回答用户关于商品、订单、退款等问题。请提供准确、有用的信息，并保持友好的态度。"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"直接查询LLM失败: {str(e)}")
            return "抱歉，我暂时无法回答您的问题，请稍后再试。"
    
    def format_chat_history(self, history: List[Dict[str, str]]) -> List[Union[HumanMessage, AIMessage]]:
        """
        格式化聊天历史
        
        Args:
            history: 聊天历史
            
        Returns:
            格式化后的聊天历史
        """
        formatted_history = []
        for message in history:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "user":
                formatted_history.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_history.append(AIMessage(content=content))
        
        return formatted_history
    
    def with_fallbacks(self):
        """
        设置LLM回退机制
        
        Returns:
            具有回退机制的LLM
        """
        # 这个方法可以实现LLM调用失败时的回退策略
        # 例如，可以设置重试逻辑或降级到其他模型
        # 目前简单返回原始LLM
        return self.llm


# 单例模式
llm_manager = LLMManager() 