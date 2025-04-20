import asyncio
import logging
import json
import os

from app.services.knowledge_service import knowledge_service
from app.core.rag_retriever import rag_retriever
from app.models.schemas import IntentType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_rag_retrieval():
    """测试RAG检索功能"""
    
    # 1. 初始化知识库
    logger.info("正在初始化知识库...")
    results = knowledge_service.init_knowledge_base()
    logger.info(f"知识库初始化结果: {results}")
    
    # 2. 测试RAG检索 - 使用通用意图和积分查询
    logger.info("\n测试积分查询 - 通用意图:")
    result = await rag_retriever.retrieve('怎样使用购物积分', IntentType.GENERAL_INQUIRY)
    logger.info(f"找到文档数量: {len(result.documents)}")
    logger.info(f"来源: {result.sources}")
    for i, doc in enumerate(result.documents):
        logger.info(f"文档{i+1}类型: {type(doc)}")
        logger.info(f"文档{i+1}内容: {doc}")
    
    # 3. 测试RAG检索 - 使用商品意图和积分查询
    logger.info("\n测试积分查询 - 商品意图:")
    result = await rag_retriever.retrieve('怎样使用购物积分', IntentType.PRODUCT_INQUIRY)
    logger.info(f"找到文档数量: {len(result.documents)}")
    logger.info(f"来源: {result.sources}")
    for i, doc in enumerate(result.documents):
        logger.info(f"文档{i+1}类型: {type(doc)}")
        logger.info(f"文档{i+1}内容: {doc}")
    
    # 4. 测试RAG多向量存储搜索
    logger.info("\n测试多向量存储搜索:")
    result = await rag_retriever.multi_vector_store_search('购物积分如何使用')
    logger.info(f"多向量存储搜索找到文档数量: {len(result.documents)}")
    logger.info(f"来源: {result.sources}")
    for i, doc in enumerate(result.documents):
        logger.info(f"文档{i+1}类型: {type(doc)}")
        if i < 2:  # 仅打印前两个文档的内容，避免输出过多
            logger.info(f"文档{i+1}内容: {doc}")
    
    # 5. 测试订单查询的RAG检索
    logger.info("\n测试订单查询:")
    result = await rag_retriever.retrieve('我的订单什么时候发货', IntentType.ORDER_STATUS)
    logger.info(f"找到文档数量: {len(result.documents)}")
    logger.info(f"来源: {result.sources}")
    if result.documents:
        logger.info(f"第一个文档内容: {result.documents[0]}")

if __name__ == "__main__":
    asyncio.run(test_rag_retrieval()) 