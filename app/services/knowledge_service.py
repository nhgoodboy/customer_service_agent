import os
import logging
import json
import glob
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.documents import Document

from config.settings import KNOWLEDGE_BASE_PATH
from app.core.vector_store import (
    product_vector_store,
    order_vector_store,
    return_refund_vector_store,
    general_vector_store,
    VectorStoreManager,
    vector_store_manager
)
from app.models.schemas import IntentType, DocumentInput
from app.utils.helpers import load_json_file, save_json_file, performance_monitor, find_files_by_pattern
from app.models.enums import KnowledgeBaseType

logger = logging.getLogger(__name__)

# 知识库类型
KNOWLEDGE_BASE_TYPES = [
    "product",           # 产品信息
    "order",             # 订单信息
    "return_refund",     # 退换货政策
    "general"            # 一般常见问题
]


class KnowledgeService:
    """知识服务，负责管理知识库数据"""
    
    def __init__(self):
        """初始化知识服务"""
        self.vector_stores = {
            IntentType.PRODUCT_INQUIRY: product_vector_store,
            IntentType.ORDER_STATUS: order_vector_store,
            IntentType.RETURN_REFUND: return_refund_vector_store,
            IntentType.GENERAL_INQUIRY: general_vector_store,
        }
        self.knowledge_base_path = KNOWLEDGE_BASE_PATH
        self.vector_store_managers = {}
        self.initialized = False
        
        logger.info("知识库服务初始化完成")
    
    async def init_knowledge_base(self) -> Dict[str, int]:
        """初始化知识库

        Returns:
            Dict[str, int]: 加载的数据统计
        """
        logger.info("开始初始化知识库...")
        if not os.path.exists(KNOWLEDGE_BASE_PATH):
            logger.error(f"知识库路径不存在: {KNOWLEDGE_BASE_PATH}")
            raise FileNotFoundError(f"知识库路径不存在: {KNOWLEDGE_BASE_PATH}")
        
        stats = {
            "product": 0,
            "order": 0,
            "return_refund": 0,
            "general": 0
        }
        
        # 清空现有的vector stores
        logger.info("清空现有的vector stores")
        await vector_store_manager.clear_vector_store(KnowledgeBaseType.PRODUCT.value)
        await vector_store_manager.clear_vector_store(KnowledgeBaseType.ORDER.value)
        await vector_store_manager.clear_vector_store(KnowledgeBaseType.RETURN_REFUND.value)
        await vector_store_manager.clear_vector_store(KnowledgeBaseType.GENERAL.value)
        
        # 加载产品信息
        product_files = glob.glob(os.path.join(KNOWLEDGE_BASE_PATH, "product_*.json"))
        if product_files:
            product_count = await self._load_files_to_knowledge_base(
                product_files,
                KnowledgeBaseType.PRODUCT.value
            )
            stats["product"] = product_count
            logger.info(f"加载了 {product_count} 个产品信息文件")
        
        # 加载订单信息
        order_files = glob.glob(os.path.join(KNOWLEDGE_BASE_PATH, "order_*.json"))
        if order_files:
            order_count = await self._load_files_to_knowledge_base(
                order_files,
                KnowledgeBaseType.ORDER.value
            )
            stats["order"] = order_count
            logger.info(f"加载了 {order_count} 个订单信息文件")
        
        # 加载退换货信息
        return_refund_files = glob.glob(os.path.join(KNOWLEDGE_BASE_PATH, "*refund*.json"))
        if return_refund_files:
            return_refund_count = await self._load_files_to_knowledge_base(
                return_refund_files,
                KnowledgeBaseType.RETURN_REFUND.value
            )
            stats["return_refund"] = return_refund_count
            logger.info(f"加载了 {return_refund_count} 个退换货信息文件")
        
        # 加载FAQ
        faq_files = glob.glob(os.path.join(KNOWLEDGE_BASE_PATH, "faq*.json"))
        if faq_files:
            faq_count = await self._load_files_to_knowledge_base(
                faq_files,
                KnowledgeBaseType.GENERAL.value
            )
            stats["general"] = faq_count
            logger.info(f"加载了 {faq_count} 个FAQ文件")
        
        self.initialized = True
        logger.info("知识库初始化完成")
        return stats

    async def _load_files_to_knowledge_base(self, file_paths: List[str], kb_type: str) -> int:
        """将文件加载到知识库
        
        Args:
            file_paths (List[str]): 文件路径列表
            kb_type (str): 知识库类型
            
        Returns:
            int: 加载的文件数量
        """
        count = 0
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 将数据处理为文档格式，添加到向量存储中
                documents = []
                
                if isinstance(data, list):
                    for item in data:
                        doc_text = json.dumps(item, ensure_ascii=False)
                        # 为每个文档添加元数据
                        metadata = {
                            "source": file_path,
                            "type": kb_type
                        }
                        documents.append({"text": doc_text, "metadata": metadata})
                else:
                    doc_text = json.dumps(data, ensure_ascii=False)
                    metadata = {
                        "source": file_path,
                        "type": kb_type
                    }
                    documents.append({"text": doc_text, "metadata": metadata})
                
                # 添加到向量存储
                await vector_store_manager.add_documents(documents, kb_type)
                count += 1
                logger.debug(f"已加载文件: {file_path} 到知识库 {kb_type}")
            except Exception as e:
                logger.error(f"加载文件 {file_path} 时出错: {str(e)}")
        
        return count
    
    @performance_monitor
    async def add_documents(self, kb_type: str, documents: List[str], metadatas: List[Dict[str, Any]] = None) -> bool:
        """
        添加文档到知识库
        
        Args:
            kb_type: 知识库类型
            documents: 文档列表
            metadatas: 元数据列表
            
        Returns:
            是否成功添加
        """
        if kb_type not in self.vector_store_managers:
            logger.error(f"未知的知识库类型: {kb_type}")
            return False
            
        if not documents:
            logger.warning("没有提供文档")
            return False
            
        try:
            # 如果没有提供元数据，创建空元数据
            if metadatas is None:
                metadatas = [{"source": "api_upload"} for _ in documents]
                
            # 添加文档到向量存储
            self.vector_store_managers[kb_type].add_texts(documents, metadatas)
            logger.info(f"已成功添加 {len(documents)} 个文档到知识库 {kb_type}")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到知识库 {kb_type} 失败: {str(e)}")
            return False
    
    @performance_monitor
    async def clear_knowledge_base(self, kb_type: Optional[str] = None) -> bool:
        """
        清除知识库
        
        Args:
            kb_type: 知识库类型，如果为None则清除所有知识库
            
        Returns:
            是否成功清除
        """
        try:
            if kb_type:
                # 清除指定类型的知识库
                if kb_type in self.vector_store_managers:
                    await self.vector_store_managers[kb_type].clear()
                    logger.info(f"已清除知识库: {kb_type}")
                else:
                    logger.warning(f"未知的知识库类型: {kb_type}")
                    return False
            else:
                # 清除所有知识库
                for kb in self.vector_store_managers.values():
                    await kb.clear()
                self.vector_store_managers = {}
                logger.info("已清除所有知识库")
                
            return True
            
        except Exception as e:
            logger.error(f"清除知识库失败: {str(e)}")
            return False
    
    @performance_monitor
    async def retrieve_knowledge(self, kb_type: str, query: str, top_k: int = 3) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        从知识库中检索知识
        
        Args:
            kb_type: 知识库类型
            query: 查询文本
            top_k: 返回的结果数量
            
        Returns:
            检索到的文档列表和其来源元数据
        """
        if kb_type not in self.vector_store_managers:
            logger.warning(f"未知的知识库类型: {kb_type}")
            return [], []
            
        try:
            # 执行相似度搜索
            docs, sources = await self.vector_store_managers[kb_type].similarity_search(
                query, 
                k=top_k
            )
            
            if not docs:
                logger.info(f"知识库 {kb_type} 中没有找到与查询相关的结果: {query}")
                return [], []
                
            # 提取文档和元数据
            doc_contents = []
            metadatas = []
            
            for i, doc in enumerate(docs):
                doc_contents.append(doc.page_content)
                metadatas.append({
                    "source": doc.metadata.get("source", "unknown"), 
                    "score": 1.0 - (i * 0.1)  # 简单模拟得分
                })
                
            logger.info(f"从知识库 {kb_type} 检索到 {len(doc_contents)} 个结果")
            return doc_contents, metadatas
            
        except Exception as e:
            logger.error(f"从知识库 {kb_type} 检索知识失败: {str(e)}")
            return [], []
    
    def find_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """根据订单ID查找订单
        
        Args:
            order_id (str): 订单ID
            
        Returns:
            Optional[Dict[str, Any]]: 订单信息，如果未找到则返回None
        """
        logger.info(f"查询订单ID: {order_id}")
        
        # 查找所有订单文件
        order_files = glob.glob(os.path.join(KNOWLEDGE_BASE_PATH, "order_*.json"))
        
        for file_path in order_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    orders = json.load(f)
                
                # 如果不是列表，转换为列表
                if not isinstance(orders, list):
                    orders = [orders]
                
                # 查找匹配订单ID的订单
                for order in orders:
                    if order.get("order_id") == order_id:
                        logger.info(f"在文件 {file_path} 中找到订单 {order_id}")
                        return order
            except Exception as e:
                logger.error(f"读取订单文件 {file_path} 时出错: {str(e)}")
        
        logger.warning(f"未找到订单ID: {order_id}")
        return None


# 单例模式
knowledge_service = KnowledgeService() 