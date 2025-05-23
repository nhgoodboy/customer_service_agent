import logging
from typing import Dict, Any, Tuple
import re

from app.models.schemas import IntentType, IntentClassificationResponse
from app.core.llm_manager import llm_manager
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class IntentClassifier:
    """意图分类器，负责识别用户查询的意图"""
    
    def __init__(self):
        """初始化意图分类器"""
        self.llm_manager = llm_manager
    
    async def classify(self, query: str) -> IntentClassificationResponse:
        """
        分类用户查询的意图
        
        Args:
            query: 用户查询文本
            
        Returns:
            意图分类结果
        """
        try:
            # 先检查是否包含订单号格式，如果包含，优先返回订单状态查询意图
            if self._contains_order_id(query):
                logger.info(f"查询包含订单号，判定为订单状态查询：{query}")
                return IntentClassificationResponse(
                    intent=IntentType.ORDER_STATUS,
                    confidence=0.95
                )
            
            intent, confidence = await self._classify_intent(query)
            return IntentClassificationResponse(
                intent=intent,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"意图分类失败: {str(e)}")
            return IntentClassificationResponse(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                message=f"意图分类失败: {str(e)}"
            )
    
    def _contains_order_id(self, query: str) -> bool:
        """
        检查查询中是否包含订单号格式
        
        Args:
            query: 用户查询文本
            
        Returns:
            是否包含订单号
        """
        # 订单号规则：OD+数字
        order_pattern = r'OD\d{10,12}'
        
        # 检查查询是否包含订单号
        has_order_id = bool(re.search(order_pattern, query))
        
        # 检查是否包含与订单相关的关键词
        order_keywords = ['订单', '包裹', '发货', '物流', '快递', '配送', '送达', '追踪', '查询', '订单号', '物流信息']
        has_order_keywords = any(keyword in query for keyword in order_keywords)
        
        # 如果同时包含订单号格式和订单关键词，或者只包含明确的订单号格式，返回True
        return has_order_id and (has_order_keywords or 'OD' in query)
    
    async def _classify_intent(self, query: str) -> Tuple[IntentType, float]:
        """
        使用LLM对查询进行意图分类
        
        Args:
            query: 用户查询文本
            
        Returns:
            (意图类型, 置信度)
        """
        try:
            # 系统提示
            intent_system_prompt = """你是一个专业的意图分类助手。你的任务是分析用户的查询并将其分类为以下意图类别之一：
- product_inquiry: 与商品相关的咨询，如商品功能、规格、库存等
- order_status: 与订单状态相关的查询，如订单跟踪、发货状态等
- return_refund: 与退货退款相关的查询，如退货流程、退款状态等
- general_inquiry: 其他一般性问题，如账户问题、平台政策等

注意：如果查询中包含订单号（如OD开头的数字组合）或提到"订单状态"、"物流"、"发货"等内容，应该优先考虑order_status意图。

仅返回最匹配的意图类别名称，不要返回任何其他内容。
"""
            
            # 直接使用LLM进行调用，避免使用链
            messages = [
                SystemMessage(content=intent_system_prompt),
                HumanMessage(content=query)
            ]
            
            try:
                response = await self.llm_manager.llm.ainvoke(messages)
                # 处理不同类型的响应格式
                if hasattr(response, 'content'):
                    intent_text = response.content.strip().lower()
                elif isinstance(response, str):
                    intent_text = response.strip().lower()
                else:
                    intent_text = str(response).strip().lower()
            except Exception as e:
                logger.error(f"调用意图分类LLM失败: {str(e)}")
                # 使用直接查询作为备选方案
                intent_text = self.llm_manager.direct_query(query, intent_system_prompt).strip().lower()
            
            # 映射到IntentType枚举
            if "product" in intent_text or "product_inquiry" in intent_text:
                intent = IntentType.PRODUCT_INQUIRY
                confidence = 0.9
            elif "order" in intent_text or "order_status" in intent_text:
                intent = IntentType.ORDER_STATUS
                confidence = 0.9
            elif "return" in intent_text or "refund" in intent_text or "return_refund" in intent_text:
                intent = IntentType.RETURN_REFUND
                confidence = 0.9
            elif "general" in intent_text or "general_inquiry" in intent_text:
                intent = IntentType.GENERAL_INQUIRY
                confidence = 0.9
            else:
                # 如果无法确定意图，返回Unknown
                logger.warning(f"无法识别的意图: '{intent_text}'，查询: '{query}'")
                intent = IntentType.UNKNOWN
                confidence = 0.5
            
            logger.info(f"意图分类结果: 查询='{query}', 分类='{intent}', 置信度={confidence}")
            return intent, confidence
            
        except Exception as e:
            logger.error(f"意图分类过程中发生错误: {str(e)}")
            # 发生错误时返回Unknown
            return IntentType.UNKNOWN, 0.0


# 单例模式
intent_classifier = IntentClassifier() 