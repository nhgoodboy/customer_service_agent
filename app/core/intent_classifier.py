import logging
from typing import Dict, Any, Tuple

from app.models.schemas import IntentType, IntentClassificationResponse
from app.core.llm_manager import llm_manager

logger = logging.getLogger(__name__)


class IntentClassifier:
    """意图分类器，负责识别用户查询的意图"""
    
    def __init__(self):
        """初始化意图分类器"""
        self.llm_manager = llm_manager
        self.intent_classification_chain = llm_manager.get_intent_classification_chain()
    
    async def classify(self, query: str) -> IntentClassificationResponse:
        """
        分类用户查询的意图
        
        Args:
            query: 用户查询文本
            
        Returns:
            意图分类结果
        """
        try:
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
    
    async def _classify_intent(self, query: str) -> Tuple[IntentType, float]:
        """
        使用LLM对查询进行意图分类
        
        Args:
            query: 用户查询文本
            
        Returns:
            (意图类型, 置信度)
        """
        try:
            # 调用意图分类链
            intent_text = await self.intent_classification_chain.ainvoke({"query": query})
            
            # 清理和标准化LLM输出
            intent_text = intent_text.strip().lower()
            
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