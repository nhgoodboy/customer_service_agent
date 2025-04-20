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
            chunk_overlap=200,  # 增加重叠以获取更好的上下文连续性
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
                # 为文档添加上下文丰富的表示
                doc = self._enrich_document_with_context(doc)
                doc_chunks = self.text_splitter.split_documents([doc])
                chunks.extend(doc_chunks)
            
            # 添加到向量存储
            self.vector_store.add_documents(chunks)
            
            logger.info(f"成功添加{len(chunks)}个文档块到向量存储")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到向量存储失败: {str(e)}")
            return False
    
    def _enrich_document_with_context(self, doc: Document) -> Document:
        """
        为文档添加上下文信息，增强检索效果
        
        Args:
            doc: 原始文档对象
            
        Returns:
            增强后的文档对象
        """
        # 获取文档内容和元数据
        content = doc.page_content
        metadata = doc.metadata.copy() if doc.metadata else {}
        
        # 检查内容是否是JSON格式
        if content.startswith('{') and content.endswith('}'):
            try:
                # 解析JSON
                content_json = json.loads(content)
                
                # 为FAQ文档添加特殊处理
                if metadata.get('type') == 'faq' or (isinstance(content_json, dict) and 'question' in content_json and 'answer' in content_json):
                    # 已经是FAQ格式，保持原样
                    return doc
                
                # 为普通JSON文档创建更易于检索的文本表示
                enhanced_content = []
                for key, value in content_json.items():
                    if isinstance(value, (str, int, float, bool)):
                        enhanced_content.append(f"{key}: {value}")
                    elif isinstance(value, (list, dict)):
                        enhanced_content.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                
                # 保留原始JSON内容的同时，添加更易于理解的表示
                if enhanced_content:
                    # 拼接增强内容和原始内容
                    new_content = "\n".join(enhanced_content) + "\n原始数据: " + content
                    return Document(page_content=new_content, metadata=metadata)
            except:
                # 解析JSON失败，使用原始内容
                pass
        
        # 返回原始文档
        return doc
    
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
            # 首先尝试使用增强查询技术
            enhanced_query = self._create_enhanced_query(query)
            docs = self.vector_store.similarity_search(enhanced_query, k=k)
            logger.info(f"查询: '{query}' 返回了 {len(docs)} 个相似文档")
            return docs
        except Exception as e:
            logger.error(f"相似度搜索失败: {str(e)}")
            return []
    
    def _create_enhanced_query(self, query: str) -> str:
        """
        创建增强查询，提高检索精度
        
        Args:
            query: 原始查询
            
        Returns:
            增强后的查询
        """
        # 对于短查询，可以适当扩展以提高召回率
        if len(query) < 10:
            # 检查是否包含特定关键词，如"积分"
            if "积分" in query:
                return f"{query} 购物积分 会员积分 积分使用 积分规则"
            elif "订单" in query:
                return f"{query} 订单状态 物流 配送 发货"
            elif "退款" in query or "退货" in query:
                return f"{query} 退货政策 退款流程 售后"
            
        # 返回原始查询
        return query
    
    def get_relevant_documents(self, query: str, k: int = 5) -> List[Document]:
        """
        获取与查询相关的文档
        
        Args:
            query: 查询文本
            k: 返回的结果数量
            
        Returns:
            相关文档列表
        """
        # 增强查询
        enhanced_query = self._create_enhanced_query(query)
        return self.vector_store.similarity_search(enhanced_query, k=k)
    
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
            
            # 文件名作为源
            file_name = os.path.basename(file_path)
            
            if isinstance(data, list):
                # 如果是列表，添加每个项目
                for item in data:
                    if isinstance(item, dict):
                        # 为每个条目创建上下文丰富的表示
                        item_str = json.dumps(item, ensure_ascii=False)
                        
                        # 添加文件名作为上下文信息
                        metadata = {"source": file_name}
                        
                        # 检查是否是FAQ格式
                        if "question" in item and "answer" in item:
                            metadata["type"] = "faq"
                            metadata["question"] = item["question"]
                            
                            # 创建富化内容
                            content = f"问题: {item['question']}\n回答: {item['answer']}"
                            if "category" in item:
                                content += f"\n类别: {item['category']}"
                                metadata["category"] = item["category"]
                            
                            documents.append(Document(
                                page_content=content,
                                metadata=metadata
                            ))
                        else:
                            documents.append(Document(
                                page_content=item_str,
                                metadata=metadata
                            ))
                    else:
                        documents.append(Document(
                            page_content=str(item),
                            metadata={"source": file_name}
                        ))
            elif isinstance(data, dict):
                # 如果是字典，添加整个字典
                text = json.dumps(data, ensure_ascii=False)
                documents.append(Document(
                    page_content=text,
                    metadata={"source": file_name}
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