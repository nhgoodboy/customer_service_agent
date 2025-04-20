@echo off
SETLOCAL

REM 检查虚拟环境是否存在
IF NOT EXIST venv (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查依赖是否已安装
pip freeze | findstr "fastapi" >nul
IF %ERRORLEVEL% NEQ 0 (
    echo 安装依赖...
    pip install -r requirements.txt
)

REM 检查知识库目录是否存在
IF NOT EXIST data\knowledge_base (
    echo 创建知识库目录...
    mkdir data\knowledge_base
)

REM 启动服务
echo 启动服务...
uvicorn main:app --reload --host 0.0.0.0 --port 8000

ENDLOCAL 