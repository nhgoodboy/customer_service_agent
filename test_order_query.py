import asyncio
import logging
import json
import os

from app.services.knowledge_service import knowledge_service
from app.services.chat_service import chat_service
from app.models.schemas import ChatRequest
from config.settings import KNOWLEDGE_BASE_PATH

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_order_query():
    """测试订单查询功能"""
    
    # 1. 初始化知识库
    logger.info("正在初始化知识库...")
    results = knowledge_service.init_knowledge_base()
    logger.info(f"知识库初始化结果: {results}")
    
    # 2. 直接测试订单查询功能
    order_id = "OD2023110512567"
    logger.info(f"直接测试查询订单: {order_id}")
    
    # 2.1 使用知识服务查询
    order_info = knowledge_service.find_order_by_id(order_id)
    if order_info:
        logger.info(f"知识服务找到订单: {order_id}")
        logger.info(f"订单状态: {order_info.get('status')}")
    else:
        logger.error(f"知识服务未找到订单: {order_id}")
        
        # 2.2 直接读取文件测试
        file_path = os.path.join(KNOWLEDGE_BASE_PATH, "order_samples.json")
        logger.info(f"尝试直接读取文件: {file_path}")
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                orders = json.load(f)
                
            logger.info(f"文件中包含 {len(orders)} 条订单记录")
            
            # 搜索订单号
            found = False
            for order in orders:
                if isinstance(order, dict) and order.get("order_id") == order_id:
                    logger.info(f"在文件中找到订单 {order_id}")
                    found = True
                    break
            
            if not found:
                logger.error(f"文件中未找到订单 {order_id}")
        else:
            logger.error(f"订单文件不存在: {file_path}")
    
    # 3. 测试聊天服务的订单查询功能
    logger.info("测试聊天服务的订单查询功能")
    
    # 3.1 创建聊天请求
    request = ChatRequest(
        query=f"我想查询一下订单号为{order_id}的状态",
        session_id="test_session"
    )
    
    # 3.2 处理聊天请求
    response = await chat_service.process_chat(request)
    
    # 3.3 输出结果
    logger.info(f"聊天响应: {response.response}")
    logger.info(f"意图识别: {response.intent}")
    logger.info(f"参考源: {response.sources}")
    
    # 3.4 再次测试，使用更自然的查询语句
    request = ChatRequest(
        query=f"你好，能帮我查一下订单OD2023110512567的物流信息吗？",
        session_id="test_session"
    )
    
    response = await chat_service.process_chat(request)
    logger.info(f"自然语言查询响应: {response.response}")

if __name__ == "__main__":
    asyncio.run(test_order_query()) 