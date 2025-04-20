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

async def test_points_query():
    """测试购物积分查询功能"""
    
    # 1. 初始化知识库
    logger.info("正在初始化知识库...")
    results = knowledge_service.init_knowledge_base()
    logger.info(f"知识库初始化结果: {results}")
    
    # 2. 测试购物积分查询功能
    logger.info("测试积分查询功能")
    
    # 2.1 直接从FAQ中读取积分信息
    faq_path = os.path.join(KNOWLEDGE_BASE_PATH, "faq.json")
    logger.info(f"尝试读取FAQ文件: {faq_path}")
    
    if os.path.exists(faq_path):
        with open(faq_path, 'r', encoding='utf-8') as f:
            faq_data = json.load(f)
        
        logger.info(f"FAQ文件包含 {len(faq_data)} 个类别")
        
        # 搜索积分相关问题
        found_points = False
        for category in faq_data:
            if "questions" in category:
                for question in category["questions"]:
                    if "积分" in question.get("question", ""):
                        logger.info(f"在FAQ中找到积分信息: {question.get('question')}")
                        logger.info(f"积分信息内容: {question.get('answer')}")
                        found_points = True
                        break
                if found_points:
                    break
        
        if not found_points:
            logger.error("未在FAQ中找到积分相关信息")
    else:
        logger.error(f"FAQ文件不存在: {faq_path}")
    
    # 3. 测试聊天服务的积分查询功能
    logger.info("测试聊天服务的积分查询功能")
    
    # 3.1 创建聊天请求
    request = ChatRequest(
        query="怎样使用购物积分",
        session_id="test_points_session"
    )
    
    # 3.2 处理聊天请求
    response = await chat_service.process_chat(request)
    
    # 3.3 输出结果
    logger.info(f"聊天响应: {response.response}")
    logger.info(f"意图识别: {response.intent}")
    logger.info(f"参考源: {response.sources}")
    
    # 3.4 使用另一种表达方式测试
    request = ChatRequest(
        query="请问积分怎么用？可以抵扣多少钱？",
        session_id="test_points_session"
    )
    
    response = await chat_service.process_chat(request)
    logger.info(f"第二次查询响应: {response.response}")

if __name__ == "__main__":
    asyncio.run(test_points_query()) 