import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础目录
BASE_DIR = Path(__file__).resolve().parent.parent

# API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = "deepseek-chat"

# 意图识别配置
INTENT_TYPES = {
    "product_inquiry": "商品咨询",
    "order_status": "订单状态",
    "return_refund": "退货退款",
    "general_inquiry": "一般问题"
}

# 向量数据库配置
VECTOR_STORE_PATH = os.path.join(BASE_DIR, "data", "vector_store")

# 知识库配置
KNOWLEDGE_BASE_PATH = os.path.join(BASE_DIR, "data", "knowledge_base")

# LangChain配置
LANGCHAIN_VERBOSE = True
TEMPERATURE = 0.7
MAX_TOKENS = 2048

# 服务器配置
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000 