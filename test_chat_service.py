#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
from app.models.schemas import ChatRequest
from app.services.chat_service import chat_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_chat_service")

async def test_chat_service():
    """测试聊天服务"""
    logger.info("开始测试聊天服务...")
    
    # 测试1：简单问候
    query1 = "你好，今天能发货吗"
    session_id = "test_session_123"
    
    logger.info(f"测试查询1: {query1}")
    chat_request = ChatRequest(
        query=query1,
        session_id=session_id
    )
    
    response = await chat_service.process_chat(chat_request)
    
    logger.info(f"意图: {response.intent}")
    logger.info(f"回复: {response.response}")
    if response.sources:
        logger.info(f"源: {response.sources}")
    
    # 测试2：订单查询
    query2 = "我想查询订单 OD2023110512567 的状态"
    
    logger.info(f"\n测试查询2: {query2}")
    chat_request = ChatRequest(
        query=query2,
        session_id=session_id
    )
    
    response = await chat_service.process_chat(chat_request)
    
    logger.info(f"意图: {response.intent}")
    logger.info(f"回复: {response.response}")
    if response.sources:
        logger.info(f"源: {response.sources}")
    
    logger.info("聊天服务测试完成")

if __name__ == "__main__":
    asyncio.run(test_chat_service()) 