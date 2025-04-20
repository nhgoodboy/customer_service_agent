import asyncio
import logging
import os
import sys
from app.models.schemas import ChatRequest
from app.services.chat_service import ChatService
from app.services.knowledge_service import KnowledgeService

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_chat_with_order")

async def test_chat_with_order():
    logger.info("开始测试聊天服务中的订单查询...")
    
    # 初始化知识库
    knowledge_service = KnowledgeService()
    await knowledge_service.init_knowledge_base()
    
    # 初始化聊天服务
    chat_service = ChatService()
    
    # 测试1：直接询问订单号
    query1 = "我想查询订单 OD2023110512567 的状态"
    session_id = "test_session_123"
    
    chat_request = ChatRequest(
        session_id=session_id,
        query=query1,
        system_prompt="你是一个友好的客服助手"
    )
    
    logger.info(f"测试查询: {query1}")
    chat_response = await chat_service.process_chat(chat_request)
    
    logger.info(f"意图识别: {chat_response.intent}")
    logger.info(f"回复: {chat_response.response}")
    if chat_response.sources:
        logger.info(f"参考文档: {chat_response.sources}")
    
    # 测试2：更自然的查询方式
    query2 = "我的笔记本订单OD2023110512567什么时候能到货？"
    
    chat_request = ChatRequest(
        session_id=session_id,
        query=query2,
        system_prompt="你是一个友好的客服助手"
    )
    
    logger.info(f"\n测试查询: {query2}")
    chat_response = await chat_service.process_chat(chat_request)
    
    logger.info(f"意图识别: {chat_response.intent}")
    logger.info(f"回复: {chat_response.response}")
    if chat_response.sources:
        logger.info(f"参考文档: {chat_response.sources}")

def main():
    print(f"Python版本: {sys.version}")
    asyncio.run(test_chat_with_order())

if __name__ == "__main__":
    main() 