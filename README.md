# 客服智能体系统

基于RAG（检索增强生成）技术的智能客服系统，能根据用户意图检索相关知识并生成个性化回复。系统支持多种电商场景，包括产品咨询、订单查询、退货退款和一般咨询等。

## 系统特点

- **意图识别**：自动识别用户查询的意图类型
- **知识库检索**：基于向量检索技术，从相应知识库获取相关信息
- **上下文感知对话**：保持对话历史，提供连贯的交互体验
- **会话管理**：支持多用户会话，包括创建、保存和清理
- **知识库管理**：支持知识库的初始化、添加和清空操作
- **网页客户端**：提供美观直观的聊天界面，支持会话管理
- **健壮的RAG系统**：优化的检索策略和文档处理，确保高质量知识检索

## 技术架构

- **后端**：FastAPI提供API服务
- **前端**：HTML, CSS和JavaScript构建的响应式网页客户端
- **大模型**：DeepSeek大语言模型
- **向量存储**：ChromaDB存储知识嵌入向量
- **嵌入模型**：使用HuggingFace中文嵌入模型
- **模板引擎**：使用Jinja2进行HTML模板渲染

## RAG系统健壮性设计

我们的系统实现了多层次的健壮性优化，使RAG系统能够应对各种检索挑战：

### 文档处理优化

- **增强型文档表示**：通过`_enrich_document_with_context`方法为每个文档添加丰富的上下文信息，提高语义理解
- **FAQ专用处理**：为常见问题集实现了专门的处理流程`_load_faq_to_vector_store`，保持问答对的语义完整性
- **优化的文本分块**：采用200字符的分块重叠，保证上下文连贯性不被破坏

### 多层次检索策略

- **增强查询扩展**：通过`_create_enhanced_query`方法根据关键词智能扩展查询，提高相关文档召回率
- **多向量存储检索**：`multi_vector_store_search`方法允许跨知识库域查询，特别适用于"积分"等跨领域概念
- **关键词触发策略**：对积分、会员等特定关键词自动启用跨域检索策略
- **补充检索机制**：当主要检索结果不足时，自动从相关知识库补充内容

### 检索结果优化

- **LLM驱动的重排序**：通过`_rerank_documents`利用LLM对检索结果进行相关性重排序
- **去重和合并**：在混合检索结果中确保内容无冗余
- **文档类型感知处理**：根据文档类型（JSON、FAQ等）进行专门处理，确保内容正确呈现

### 实际应用案例

**积分查询问题解决**：
系统最初在处理"购物积分如何使用"等查询时无法检索到正确信息，即使数据存在于知识库中。通过实施以下改进，我们成功解决了这个问题：

1. 优化FAQ数据加载过程，确保积分相关问题被正确向量化
2. 实现专门的文档表示和内容增强
3. 添加跨知识库域的多向量检索
4. 实现关键词触发的智能检索策略
5. 使用LLM进行检索结果重排序

这些改进确保了系统能够可靠地找到并提供积分相关信息，展示了我们的RAG系统的健壮性和适应性。

## 安装指南

### 环境要求

- Python 3.9+
- 足够的磁盘空间用于向量存储（至少1GB）
- DeepSeek API密钥

### 安装步骤

1. **克隆代码库**

```bash
git clone https://github.com/your-username/customer_service_agent.git
cd customer_service_agent
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
```

3. **安装依赖库**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

创建`.env`文件并设置以下参数：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_MODEL=deepseek-chat
TEMPERATURE=0.7
MAX_TOKENS=1024
KNOWLEDGE_BASE_PATH=./data/knowledge_base
```

5. **准备知识库文件**

将知识库文件放置在`data/knowledge_base`目录下，命名规范：
- 产品信息：`product_*.json`
- 订单信息：`order_*.json`
- 退货退款信息：`*refund*.json`
- 常见问题：`faq*.json`

6. **启动服务**

```bash
uvicorn main:app --reload
```

服务将在 http://localhost:8000 启动

## 使用指南

### 网页客户端

1. 启动服务器后，访问 http://localhost:8000 即可打开网页聊天界面
2. 在聊天输入框中输入您的问题并按回车键或点击发送按钮
3. 系统会自动分析您的问题，从知识库检索相关信息并给出回答
4. 您可以点击"新对话"按钮开始一个新的会话
5. 点击左侧的对话列表可以切换不同的会话
6. 点击"清空历史"按钮可以清除所有会话记录

### API使用指南

#### 1. 初始化知识库

```
POST /api/knowledge/init
```

初始化所有知识库，加载知识文件到向量存储。

#### 2. 创建会话

```
POST /api/session/create
```

**响应示例**:
```json
{
  "session_id": "f8d7e6c5-a4b3-c2d1-e0f9-g8h7i6j5k4l3"
}
```

#### 3. 聊天接口

```
POST /api/chat
```

**请求体**:
```json
{
  "query": "这款手机有什么特点？",
  "session_id": "f8d7e6c5-a4b3-c2d1-e0f9-g8h7i6j5k4l3"
}
```

**响应示例**:
```json
{
  "response": "这款手机采用了6.7英寸OLED高刷屏幕，搭载最新处理器，电池容量5000mAh，支持快充技术，拥有4800万像素主摄和优秀的夜景模式。",
  "intent": "product_inquiry",
  "sources": ["product_phones.json"]
}
```

#### 4. 查看会话历史

```
GET /api/session/{session_id}/history
```

返回指定会话的对话历史记录。

#### 5. 清除会话

```
DELETE /api/session/{session_id}
```

清除指定会话的历史记录。

#### 6. 添加知识

```
POST /api/knowledge/add
```

**请求体**:
```json
{
  "document": {
    "text": "新款XYZ手机支持5G网络，采用最新处理器，屏幕尺寸6.7英寸",
    "metadata": {
      "source": "产品手册",
      "id": "product_001"
    }
  },
  "intent_type": "product_inquiry"
}
```

#### 7. 健康检查

```
GET /api/health
```

## 前端开发指南

网页客户端位于以下目录：

- `templates/index.html` - 主HTML模板
- `static/css/style.css` - CSS样式
- `static/js/main.js` - JavaScript交互逻辑

如果您想修改前端界面，可以编辑这些文件。前端使用了原生JavaScript，没有依赖任何前端框架，便于理解和修改。

## 常见问题

1. **DeepSeek API密钥警告**

如果看到API密钥参数警告，可以修改`app/core/llm_manager.py`文件，使用`model_kwargs`传递API密钥：

```python
self._llm = ChatDeepSeek(
    model=DEEPSEEK_MODEL,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
    model_kwargs={"deepseek_api_key": DEEPSEEK_API_KEY}
)
```

2. **向量存储初始化错误**

如果遇到Chroma向量存储错误，请确保已安装最新版本的依赖库：

```bash
pip install --upgrade langchain-community langchain-chroma
```

3. **JSON文件解析错误**

确保知识库中的JSON文件格式正确，可以使用在线JSON验证工具检查。

4. **网页界面无法访问**

如果无法访问网页界面，请检查：
- 服务器是否正常运行
- 浏览器控制台是否显示错误信息
- 访问的URL是否正确（应为 http://localhost:8000）

## 参考资料

* [RbFT: Robust Fine-tuning for Retrieval-Augmented Generation against Retrieval Defects](https://arxiv.org/html/2501.18365v1) - 关于RAG系统健壮性设计的研究论文，探讨了检索缺陷及其解决方法

## 贡献

欢迎提交问题和改进建议，共同完善这个系统！

## 许可证

MIT 