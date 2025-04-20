import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from fastapi.routing import APIRoute

from app.api import router
from app.services.knowledge_service import knowledge_service
from config.settings import SERVER_HOST, SERVER_PORT

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="企业级电商客服智能体",
    description="基于DeepSeek的企业级电商客服智能体API",
    version="0.1.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，可以根据需要设置为特定域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有HTTP头
)

# 设置静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 注册路由
app.include_router(router, prefix="/api")

# 添加/chat路由，重定向到/api/chat
@app.post("/chat")
async def chat_redirect(request: Request):
    """
    /chat路由重定向到/api/chat
    """
    body = await request.json()
    from app.api.routes import chat
    from app.models.schemas import ChatRequest
    return await chat(ChatRequest(**body))

@app.get("/chat")
async def chat_get_handler():
    """
    GET请求/chat路径的处理器，提供友好的错误信息
    """
    return JSONResponse(
        status_code=400,
        content={
            "detail": "聊天接口需要使用POST方法",
            "message": "请使用POST方法访问/api/chat或/chat，并在请求体中提供必要的参数"
        }
    )

# 添加前端页面路由
@app.get("/")
async def index(request: Request):
    """
    返回前端聊天界面
    """
    return templates.TemplateResponse("index.html", {"request": request})

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"全局异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误", "message": str(exc)}
    )


# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("服务启动中...")
    
    # 初始化知识库
    try:
        results = knowledge_service.init_knowledge_base()
        logger.info(f"知识库初始化结果: {results}")
    except Exception as e:
        logger.error(f"知识库初始化失败: {str(e)}")
    
    logger.info("服务启动完成")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("服务关闭中...")
    logger.info("服务已关闭")


if __name__ == "__main__":
    # 启动服务
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info"
    ) 