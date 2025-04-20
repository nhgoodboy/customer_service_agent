#!/bin/bash

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖是否已安装
if ! pip freeze | grep -q "fastapi"; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

# 检查知识库目录是否存在
if [ ! -d "data/knowledge_base" ]; then
    echo "创建知识库目录..."
    mkdir -p data/knowledge_base
fi

# 启动服务
echo "启动服务..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 