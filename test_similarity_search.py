#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging

from app.core.vector_store import product_vector_store

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_similarity_search")

async def test_similarity_search():
    """测试similarity_search方法"""
    logger.info("开始测试similarity_search方法...")
    
    # 测试查询
    query = "手机配置"
    logger.info(f"测试查询: {query}")
    
    try:
        # 执行相似度搜索
        docs, sources = await product_vector_store.similarity_search(query, k=3)
        
        logger.info(f"搜索结果: 找到 {len(docs)} 个文档")
        
        # 输出文档内容
        for i, doc in enumerate(docs):
            logger.info(f"文档 {i+1}:")
            logger.info(f"内容: {doc.page_content[:100]}...")
            logger.info(f"来源: {doc.metadata.get('source', '未知')}")
        
        # 输出来源
        logger.info(f"所有来源: {sources}")
        
        logger.info("similarity_search方法测试成功")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_similarity_search()) 