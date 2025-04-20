from enum import Enum


class KnowledgeBaseType(Enum):
    """知识库类型枚举"""
    PRODUCT = "product"           # 产品信息
    ORDER = "order"               # 订单信息
    RETURN_REFUND = "return_refund"  # 退换货政策
    GENERAL = "general"           # 一般常见问题 