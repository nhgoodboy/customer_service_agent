import logging
from typing import List, Dict, Any, Optional, Tuple
import json

from langchain_core.documents import Document

from app.models.schemas import IntentType, RAGResult
from app.core.vector_store import (
    product_vector_store,
    order_vector_store,
    return_refund_vector_store,
    general_vector_store
)
from app.utils.helpers import extract_document_content

logger = logging.getLogger(__name__)


class RAGRetriever:
    """RAG检索器，根据用户意图和查询检索相关文档"""
    
    def __init__(self):
        """初始化RAG检索器"""
        self.vector_stores = {
            IntentType.PRODUCT_INQUIRY: product_vector_store,
            IntentType.ORDER_STATUS: order_vector_store,
            IntentType.RETURN_REFUND: return_refund_vector_store,
            IntentType.GENERAL_INQUIRY: general_vector_store,
            IntentType.UNKNOWN: general_vector_store  # 未知意图使用通用知识库
        }
    
    async def retrieve(self, query: str, intent: IntentType, top_k: int = 5) -> RAGResult:
        """
        检索与查询相关的文档
        
        Args:
            query: 用户查询
            intent: 查询意图类型
            top_k: 返回的文档数量
            
        Returns:
            检索结果
        """
        try:
            # 获取对应意图的向量存储
            vector_store = self.vector_stores.get(intent)
            if not vector_store:
                logger.warning(f"未找到意图 {intent} 对应的向量存储，使用通用知识库")
                vector_store = self.vector_stores[IntentType.GENERAL_INQUIRY]
            
            # 执行相似度搜索
            docs = await vector_store.similarity_search(query, k=top_k)
            
            # 提取文档内容和来源
            documents, sources = self._process_documents(docs)
            
            return RAGResult(
                documents=documents,
                sources=sources,
                query=query
            )
            
        except Exception as e:
            logger.error(f"RAG检索失败: {str(e)}")
            # 返回空结果
            return RAGResult(
                documents=[],
                sources=[],
                query=query
            )
    
    def _process_documents(self, docs: List[Document]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        处理检索到的文档
        
        Args:
            docs: 文档列表
            
        Returns:
            (处理后的文档, 文档来源)
        """
        processed_docs = []
        sources = []
        
        for doc in docs:
            # 提取文档内容
            content = doc.page_content
            metadata = doc.metadata or {}
            
            # 处理JSON格式的内容
            if content.startswith('{') and content.endswith('}'):
                try:
                    # 尝试解析JSON
                    json_content = json.loads(content)
                    processed_docs.append(json_content)
                    
                    # 添加来源信息
                    source = metadata.get("source", "未知来源")
                    if source not in sources:
                        sources.append(source)
                except:
                    # 如果无法解析JSON，使用原始内容
                    processed_docs.append({"content": content})
                    
                    source = metadata.get("source", "未知来源")
                    if source not in sources:
                        sources.append(source)
            else:
                # 非JSON内容直接添加
                processed_docs.append({"content": content})
                
                source = metadata.get("source", "未知来源")
                if source not in sources:
                    sources.append(source)
        
        return processed_docs, sources
    
    def get_retriever_for_intent(self, intent: IntentType):
        """
        获取特定意图的检索器
        
        Args:
            intent: 意图类型
            
        Returns:
            对应意图的检索器
        """
        vector_store = self.vector_stores.get(intent, self.vector_stores[IntentType.GENERAL_INQUIRY])
        return vector_store.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )
    
    async def multi_vector_store_search(self, query: str, top_k: int = 3) -> RAGResult:
        """
        在多个向量存储中搜索
        
        Args:
            query: 用户查询
            top_k: 每个向量存储返回的文档数量
            
        Returns:
            合并后的检索结果
        """
        all_docs = []
        all_sources = []
        
        # 在所有向量存储中搜索
        for intent, vector_store in self.vector_stores.items():
            if intent == IntentType.UNKNOWN:
                continue  # 跳过未知意图的向量存储
            
            try:
                # 在当前向量存储中搜索
                docs = await vector_store.similarity_search(query, k=top_k)
                
                # 将结果添加到总结果
                all_docs.extend(docs)
                
                # 提取文档来源
                for doc in docs:
                    source = doc.metadata.get("source", "未知来源")
                    if source not in all_sources:
                        all_sources.append(source)
            except Exception as e:
                logger.error(f"在 {intent} 向量存储中搜索失败: {str(e)}")
        
        # 处理文档
        processed_docs, _ = self._process_documents(all_docs)
        
        return RAGResult(
            documents=processed_docs,
            sources=all_sources,
            query=query
        )


# 单例模式
rag_retriever = RAGRetriever() 