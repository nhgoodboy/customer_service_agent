import os
import json
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config.settings import VECTOR_STORE_PATH, EMBEDDING_MODEL_NAME, DEVICE
from app.utils.helpers import performance_monitor, load_json_file, find_files_by_pattern, extract_document_content

# 设置日志
logger = logging.getLogger(__name__)


class VectorStoreManager:
    """
    向量数据库管理器，负责初始化、管理和使用ChromaDB向量数据库
    提供文档添加、相似度搜索等功能
    """

    def __init__(
        self, 
        embedding_model_name: str = EMBEDDING_MODEL_NAME,
        persist_directory: str = VECTOR_STORE_PATH,
        collection_name: str = "default",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化向量数据库管理器
        
        Args:
            embedding_model_name: 嵌入模型名称
            persist_directory: 向量数据库持久化目录
            collection_name: 集合名称
            chunk_size: 文本块大小
            chunk_overlap: 文本块重叠大小
        """
        self.embedding_model_name = embedding_model_name
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 确保持久化目录存在
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # 初始化相关组件
        self._initialize()
        
        logger.info(f"向量数据库管理器初始化完成: 集合={collection_name}, 嵌入模型={embedding_model_name}")

    def _initialize(self):
        """初始化嵌入模型、向量存储和文本分割器"""
        try:
            # 加载嵌入模型
            start_time = time.time()
            self.embedding = HuggingFaceEmbeddings(
                model_name=self.embedding_model_name,
                model_kwargs={'device': DEVICE}
            )
            logger.info(f"嵌入模型加载完成: {self.embedding_model_name}, 用时: {time.time() - start_time:.2f}秒")
            
            # 初始化向量存储
            self.vectordb = Chroma(
                embedding_function=self.embedding,
                persist_directory=self.persist_directory,
                collection_name=self.collection_name
            )
            
            # 初始化文本分割器
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                separators=["\n\n", "\n", "。", "！", "?", "？", ".", " ", ""]
            )
        except Exception as e:
            logger.error(f"初始化向量数据库组件失败: {str(e)}")
            raise

    def _create_enhanced_query(self, query: str) -> str:
        """
        根据查询内容增强查询
        
        Args:
            query: 原始查询
            
        Returns:
            增强后的查询
        """
        # 特定关键词映射，用于增强查询效果
        keyword_mapping = {
            "积分": ["积分", "会员积分", "points", "membership points"],
            "订单": ["订单", "包裹", "物流", "order", "package", "delivery"],
            "退款": ["退款", "退货", "换货", "refund", "return"],
            "产品": ["产品", "商品", "product", "item"]
        }
        
        enhanced_query = query
        
        # 检查查询是否包含特定关键词，如果包含则增强查询
        for keyword, related_terms in keyword_mapping.items():
            if any(term in query for term in related_terms):
                enhanced_query = f"{keyword} {query}"
                break
                
        return enhanced_query

    def _enrich_document_with_context(self, doc: Document) -> Document:
        """
        为文档增加上下文信息
        
        Args:
            doc: 文档对象
            
        Returns:
            增强后的文档
        """
        if hasattr(doc, 'metadata') and 'source' in doc.metadata:
            source = doc.metadata['source']
            # 处理JSON内容
            if source.endswith('.json'):
                try:
                    # 尝试解析JSON内容，提取更多上下文
                    content = doc.page_content
                    if isinstance(content, str) and (content.startswith('{') or content.startswith('[')):
                        json_data = json.loads(content)
                        if isinstance(json_data, dict) and 'content' in json_data:
                            doc.page_content = json_data['content']
                        # 可以添加更多的JSON格式处理逻辑
                except:
                    # 解析失败，保持原始内容
                    pass
        
        return doc

    @performance_monitor
    async def add_documents(self, documents: List[Any], source: Optional[str] = None) -> bool:
        """
        添加文档到向量数据库
        
        Args:
            documents: 要添加的文档列表，可以是Document对象、字典或字符串
            source: 文档来源
            
        Returns:
            是否成功添加
        """
        if not documents:
            logger.warning("没有要添加的文档")
            return False
            
        try:
            # 处理不同类型的文档输入
            docs_to_add = []
            
            for doc in documents:
                # 如果是Document对象，直接添加
                if isinstance(doc, Document):
                    docs_to_add.append(doc)
                # 如果是字典或字符串，转换为Document对象
                else:
                    if isinstance(doc, dict):
                        # 从字典中提取内容
                        content = extract_document_content(doc)
                        metadata = {'source': source} if source else {}
                        # 如果字典包含metadata字段，合并到metadata中
                        if 'metadata' in doc and isinstance(doc['metadata'], dict):
                            metadata.update(doc['metadata'])
                    else:
                        # 字符串直接作为内容
                        content = str(doc)
                        metadata = {'source': source} if source else {}
                    
                    # 添加Document对象
                    docs_to_add.append(Document(page_content=content, metadata=metadata))
            
            # 分割文档
            splits = []
            for doc in docs_to_add:
                try:
                    doc_splits = self.text_splitter.split_documents([doc])
                    splits.extend(doc_splits)
                except Exception as e:
                    logger.error(f"分割文档失败: {str(e)}")
            
            if not splits:
                logger.warning("分割后没有可用的文档片段")
                return False
                
            # 添加到向量数据库
            self.vectordb.add_documents(splits)
            self.vectordb.persist()
            
            logger.info(f"成功添加 {len(splits)} 个文档片段到向量数据库")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {str(e)}")
            return False

    @performance_monitor
    async def similarity_search(self, query: str, k: int = 3) -> Tuple[List[Document], List[str]]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            k: 返回的最相似文档数量
            
        Returns:
            相似文档列表和来源列表
        """
        try:
            # 增强查询
            enhanced_query = self._create_enhanced_query(query)
            
            # 执行相似度搜索
            docs = self.vectordb.similarity_search(enhanced_query, k=k)
            
            # 增强文档内容
            enhanced_docs = [self._enrich_document_with_context(doc) for doc in docs]
            
            # 提取来源信息
            sources = []
            for doc in enhanced_docs:
                source = doc.metadata.get('source', 'unknown') if hasattr(doc, 'metadata') else 'unknown'
                if source not in sources:
                    sources.append(source)
                    
            return enhanced_docs, sources
            
        except Exception as e:
            logger.error(f"相似度搜索失败: {str(e)}")
            return [], []

    @performance_monitor
    def import_from_json(self, json_file: str) -> bool:
        """
        从JSON文件导入数据到向量数据库
        
        Args:
            json_file: JSON文件路径
            
        Returns:
            是否成功导入
        """
        if not os.path.exists(json_file):
            logger.error(f"JSON文件不存在: {json_file}")
            return False
            
        try:
            # 加载JSON文件
            data = load_json_file(json_file)
            if not data:
                logger.error(f"JSON文件为空或格式错误: {json_file}")
                return False
                
            # 如果是列表，直接作为多个文档处理
            if isinstance(data, list):
                documents = data
            # 如果是字典，作为单个文档处理
            elif isinstance(data, dict):
                documents = [data]
            else:
                logger.error(f"JSON文件格式不支持: {json_file}")
                return False
                
            # 添加文档到向量数据库
            return self.add_documents(documents, source=json_file)
            
        except Exception as e:
            logger.error(f"从JSON文件导入数据失败: {json_file}, 错误: {str(e)}")
            return False

    async def clear(self) -> bool:
        """
        清空向量数据库
        
        Returns:
            是否成功清空
        """
        try:
            # 删除并重新创建集合
            self.vectordb._collection.delete(filter={})
            
            logger.info(f"成功清空向量数据库集合: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"清空向量数据库失败: {str(e)}")
            return False


# 创建不同领域的向量存储实例
product_vector_store = VectorStoreManager(collection_name="product_knowledge")
order_vector_store = VectorStoreManager(collection_name="order_knowledge")
return_refund_vector_store = VectorStoreManager(collection_name="return_refund_knowledge")
general_vector_store = VectorStoreManager(collection_name="general_knowledge")

# 添加管理多个向量存储的管理器
class VectorStoreManagerFacade:
    """向量存储管理器外观，管理多个向量存储实例"""
    
    def __init__(self):
        self.managers = {
            "product": product_vector_store,
            "order": order_vector_store,
            "return_refund": return_refund_vector_store,
            "general": general_vector_store
        }
    
    async def clear_vector_store(self, kb_type: str) -> bool:
        """
        清空指定类型的向量存储
        
        Args:
            kb_type: 知识库类型
            
        Returns:
            是否成功清空
        """
        if kb_type not in self.managers:
            logger.error(f"未知的知识库类型: {kb_type}")
            return False
        
        return await self.managers[kb_type].clear()
    
    async def add_documents(self, documents: List[Any], kb_type: str) -> bool:
        """
        添加文档到指定类型的向量存储
        
        Args:
            documents: 要添加的文档列表
            kb_type: 知识库类型
            
        Returns:
            是否成功添加
        """
        if kb_type not in self.managers:
            logger.error(f"未知的知识库类型: {kb_type}")
            return False
        
        return await self.managers[kb_type].add_documents(documents)

# 创建向量存储管理器外观实例
vector_store_manager = VectorStoreManagerFacade() 