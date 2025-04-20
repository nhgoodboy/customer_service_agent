import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from operator import itemgetter

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate 

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
        
        # 初始化重排序模板
        self.rerank_template = PromptTemplate.from_template(
            """你是一个帮助用户重新排序文档相关性的AI助手。请评估以下文档与用户问题的相关性。
用户问题: {query}

文档:
{documents}

请按照与用户问题的相关性高低，返回文档的序号。只需要返回以逗号分隔的序号列表，从最相关到最不相关。例如: 2,5,1,3,4
"""
        )
    
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
            docs, sources = await vector_store.similarity_search(query, k=top_k)
            
            # 如果主要向量库未返回足够的结果，从其他向量库补充
            if len(docs) < top_k * 0.6:  # 如果不足60%，从其他知识库补充
                logger.info(f"主要知识库 {intent} 返回结果不足，将从其他知识库补充")
                backup_docs = await self._retrieve_from_multiple_stores(query, intent, top_k)
                if backup_docs:
                    # 合并并去重
                    docs = self._merge_and_deduplicate_docs(docs, backup_docs)
                    docs = docs[:top_k]  # 保持最大数量
            
            # 对检索结果进行重新排序
            if len(docs) >= 3:  # 只有当有足够多的文档时才进行重排序
                docs = await self._rerank_documents(query, docs)
            
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
    
    async def _retrieve_from_multiple_stores(self, query: str, primary_intent: IntentType, k: int) -> List[Document]:
        """
        从多个向量存储中检索文档
        
        Args:
            query: 查询文本
            primary_intent: 主要意图，避免重复检索
            k: 每个存储返回的文档数量
            
        Returns:
            文档列表
        """
        docs = []
        
        # 首先从通用知识库检索
        if primary_intent != IntentType.GENERAL_INQUIRY:
            try:
                general_docs, _ = await self.vector_stores[IntentType.GENERAL_INQUIRY].similarity_search(query, k=k//2)
                docs.extend(general_docs)
            except Exception as e:
                logger.error(f"从通用知识库检索失败: {str(e)}")
        
        # 然后从与主题相关的其他知识库检索
        related_intents = self._get_related_intents(primary_intent, query)
        for intent in related_intents:
            if intent != primary_intent and intent in self.vector_stores:
                try:
                    intent_docs, _ = await self.vector_stores[intent].similarity_search(query, k=k//2)
                    docs.extend(intent_docs)
                except Exception as e:
                    logger.error(f"从意图 {intent} 知识库检索失败: {str(e)}")
        
        return docs
    
    def _get_related_intents(self, primary_intent: IntentType, query: str) -> List[IntentType]:
        """
        基于主要意图和查询内容获取相关的意图
        
        Args:
            primary_intent: 主要意图
            query: 查询文本
            
        Returns:
            相关意图列表
        """
        # 关键词匹配规则
        keywords = {
            "积分": [IntentType.GENERAL_INQUIRY, IntentType.PRODUCT_INQUIRY],
            "订单": [IntentType.ORDER_STATUS],
            "发货": [IntentType.ORDER_STATUS],
            "物流": [IntentType.ORDER_STATUS],
            "退货": [IntentType.RETURN_REFUND],
            "退款": [IntentType.RETURN_REFUND],
            "商品": [IntentType.PRODUCT_INQUIRY],
            "产品": [IntentType.PRODUCT_INQUIRY]
        }
        
        related_intents = []
        
        # 根据关键词匹配意图
        for keyword, intents in keywords.items():
            if keyword in query:
                for intent in intents:
                    if intent != primary_intent and intent not in related_intents:
                        related_intents.append(intent)
        
        # 始终添加通用意图作为备选
        if IntentType.GENERAL_INQUIRY not in related_intents and primary_intent != IntentType.GENERAL_INQUIRY:
            related_intents.append(IntentType.GENERAL_INQUIRY)
        
        return related_intents
    
    def _merge_and_deduplicate_docs(self, primary_docs: List[Document], secondary_docs: List[Document]) -> List[Document]:
        """
        合并并去重文档列表
        
        Args:
            primary_docs: 主要文档列表
            secondary_docs: 次要文档列表
            
        Returns:
            合并后的文档列表
        """
        merged_docs = list(primary_docs)
        seen_contents = {doc.page_content for doc in primary_docs}
        
        for doc in secondary_docs:
            if doc.page_content not in seen_contents:
                merged_docs.append(doc)
                seen_contents.add(doc.page_content)
        
        return merged_docs
    
    async def _rerank_documents(self, query: str, docs: List[Document]) -> List[Document]:
        """
        重新排序文档，使用简单的重排序方法
        
        Args:
            query: 查询文本
            docs: 文档列表
            
        Returns:
            重新排序的文档列表
        """
        if not docs:
            return []
            
        try:
            # 准备文档内容
            doc_texts = []
            for i, doc in enumerate(docs):
                doc_text = f"文档{i+1}: {doc.page_content[:300]}..."  # 截断过长的文档
                doc_texts.append(doc_text)
            
            # 将文档列表格式化为字符串
            docs_str = "\n\n".join(doc_texts)
            
            from app.core.llm_manager import llm_manager
            
            # 构建重排序链
            rerank_chain = (
                {"query": RunnablePassthrough(), "documents": lambda _: docs_str} 
                | self.rerank_template 
                | llm_manager.llm 
                | StrOutputParser()
            )
            
            # 运行重排序链
            result = await rerank_chain.ainvoke(query)
            
            # 解析结果，获取重排序的索引
            indices = []
            try:
                # 解析输出的索引序列，格式如 "2,5,1,3,4"
                for idx_str in re.findall(r'\d+', result):
                    idx = int(idx_str) - 1  # 将1-based索引转换为0-based
                    if 0 <= idx < len(docs) and idx not in indices:
                        indices.append(idx)
            except Exception as e:
                logger.error(f"解析重排序结果失败: {str(e)} - {result}")
                return docs  # 失败时返回原始排序
            
            # 确保所有原始文档都包含在内
            for i in range(len(docs)):
                if i not in indices:
                    indices.append(i)
            
            # 根据新的顺序重新组织文档
            reranked_docs = [docs[idx] for idx in indices if idx < len(docs)]
            
            return reranked_docs
        except Exception as e:
            logger.error(f"重新排序文档失败: {str(e)}")
            return docs  # 失败时返回原始排序
    
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
            
            # 检查内容格式
            try:
                # 检查是否为FAQ格式
                if metadata.get("type") == "faq":
                    # 处理FAQ格式的文档
                    faq_data = {
                        "type": "faq",
                        "question": metadata.get("question", ""),
                        "content": content
                    }
                    if "category" in metadata:
                        faq_data["category"] = metadata["category"]
                    processed_docs.append(faq_data)
                    
                    source = metadata.get("source", "未知来源")
                    if source not in sources:
                        sources.append(source)
                # 处理JSON格式的内容
                elif content.startswith('{') and content.endswith('}'):
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
            except Exception as e:
                logger.error(f"处理文档时出错: {str(e)}")
                # 出错时添加原始内容
                processed_docs.append({"content": content})
                source = metadata.get("source", "未知来源")
                if source not in sources:
                    sources.append(source)
        
        return processed_docs, sources
    
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
                docs, sources = await vector_store.similarity_search(query, k=top_k)
                
                # 将结果添加到总结果
                all_docs.extend(docs)
                
                # 添加来源
                for source in sources:
                    if source not in all_sources:
                        all_sources.append(source)
            except Exception as e:
                logger.error(f"在 {intent} 向量存储中搜索失败: {str(e)}")
        
        # 对所有文档进行重新排序
        if len(all_docs) >= 3:
            all_docs = await self._rerank_documents(query, all_docs)
        
        # 处理文档
        processed_docs, _ = self._process_documents(all_docs)
        
        return RAGResult(
            documents=processed_docs,
            sources=all_sources,
            query=query
        )


# 单例模式
rag_retriever = RAGRetriever() 