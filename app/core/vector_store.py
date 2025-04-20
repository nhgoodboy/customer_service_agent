import os
import json
import logging
from typing import List, Dict, Any, Optional, Union

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import VECTOR_STORE_PATH
from app.utils.helpers import load_json_file, extract_document_content

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """向量存储管理器，负责管理和操作ChromaDB向量数据库"""
    
    def __init__(self, collection_name: str = "customer_service"):
        """
        初始化向量存储管理器
        
        Args:
            collection_name: 集合名称
        """
        self.collection_name = collection_name
        self.embedding_model = self._get_embeddings()
        self.vector_store = self._initialize_vector_store()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _get_embeddings(self) -> Embeddings:
        """
        获取嵌入模型
        
        Returns:
            嵌入模型实例
        """
        try:
            # 使用本地缓存的嵌入模型以提高性能
            cache_dir = os.path.join(VECTOR_STORE_PATH, "embeddings_cache")
            
            # 确保缓存目录存在
            os.makedirs(cache_dir, exist_ok=True)
            
            # 使用HuggingFace模型 - 可以根据需要更换不同的模型
            underlying_embeddings = HuggingFaceEmbeddings(
                model_name="shibing624/text2vec-base-chinese",
                model_kwargs={'device': 'cpu'}
            )
            
            # 使用缓存提高性能
            cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
                underlying_embeddings,
                LocalFileStore(cache_dir)
            )
            
            return cached_embeddings
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {str(e)}")
            # 作为后备，直接使用基础模型
            return HuggingFaceEmbeddings(
                model_name="shibing624/text2vec-base-chinese",
                model_kwargs={'device': 'cpu'}
            )
    
    def _initialize_vector_store(self) -> Chroma:
        """
        初始化向量存储
        
        Returns:
            ChromaDB客户端实例
        """
        # 确保向量存储目录存在
        persist_directory = os.path.join(VECTOR_STORE_PATH, self.collection_name)
        os.makedirs(persist_directory, exist_ok=True)
        
        # 初始化ChromaDB
        vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_model,
            persist_directory=persist_directory
        )
        
        return vector_store
    
    def add_documents(self, documents: List[Union[Document, Dict[str, Any], str]]) -> bool:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表，可以是langchain Document对象、字典或字符串
            
        Returns:
            是否成功添加
        """
        try:
            # 根据文档类型进行转换
            processed_docs = []
            
            for doc in documents:
                if isinstance(doc, Document):
                    processed_docs.append(doc)
                elif isinstance(doc, dict):
                    # 如果是字典，转换为Document对象
                    if "text" in doc or "content" in doc:
                        text = doc.get("text", doc.get("content", ""))
                        metadata = doc.get("metadata", {})
                        processed_docs.append(Document(page_content=text, metadata=metadata))
                    else:
                        # 如果字典中没有text或content字段，将整个字典序列化为文本
                        text = json.dumps(doc, ensure_ascii=False)
                        processed_docs.append(Document(page_content=text, metadata={"source": "json_data"}))
                elif isinstance(doc, str):
                    # 如果是字符串，直接创建Document
                    processed_docs.append(Document(page_content=doc, metadata={"source": "text_data"}))
            
            # 对文档进行分块
            chunks = []
            for doc in processed_docs:
                doc_chunks = self.text_splitter.split_documents([doc])
                chunks.extend(doc_chunks)
            
            # 添加到向量存储
            self.vector_store.add_documents(chunks)
            
            logger.info(f"成功添加{len(chunks)}个文档块到向量存储")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到向量存储失败: {str(e)}")
            return False
    
    async def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        执行相似度搜索
        
        Args:
            query: 查询文本
            k: 返回的结果数量
            
        Returns:
            相似文档列表
        """
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            logger.info(f"查询: '{query}' 返回了 {len(docs)} 个相似文档")
            return docs
        except Exception as e:
            logger.error(f"相似度搜索失败: {str(e)}")
            return []
    
    def get_relevant_documents(self, query: str, k: int = 5) -> List[Document]:
        """
        获取与查询相关的文档
        
        Args:
            query: 查询文本
            k: 返回的结果数量
            
        Returns:
            相关文档列表
        """
        return self.vector_store.similarity_search(query, k=k)
    
    def clear(self) -> bool:
        """
        清空向量存储
        
        Returns:
            是否成功清空
        """
        try:
            self.vector_store.delete_collection()
            self.vector_store = self._initialize_vector_store()
            logger.info(f"成功清空向量存储集合: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"清空向量存储失败: {str(e)}")
            return False
    
    def import_from_json(self, file_path: str) -> bool:
        """
        从JSON文件导入数据
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            是否成功导入
        """
        try:
            data = load_json_file(file_path)
            if not data:
                logger.error(f"无法加载JSON文件: {file_path}")
                return False
            
            # 处理不同类型的JSON数据结构
            documents = []
            
            if isinstance(data, list):
                # 如果是列表，添加每个项目
                for item in data:
                    if isinstance(item, dict):
                        text = json.dumps(item, ensure_ascii=False)
                        documents.append(Document(
                            page_content=text,
                            metadata={"source": os.path.basename(file_path)}
                        ))
                    else:
                        documents.append(Document(
                            page_content=str(item),
                            metadata={"source": os.path.basename(file_path)}
                        ))
            elif isinstance(data, dict):
                # 如果是字典，添加整个字典
                text = json.dumps(data, ensure_ascii=False)
                documents.append(Document(
                    page_content=text,
                    metadata={"source": os.path.basename(file_path)}
                ))
            
            # 添加文档
            return self.add_documents(documents)
            
        except Exception as e:
            logger.error(f"从JSON文件导入数据失败: {str(e)}")
            return False


# 创建不同领域的向量存储实例
product_vector_store = VectorStoreManager(collection_name="product_knowledge")
order_vector_store = VectorStoreManager(collection_name="order_knowledge")
return_refund_vector_store = VectorStoreManager(collection_name="return_refund_knowledge")
general_vector_store = VectorStoreManager(collection_name="general_knowledge") 