import os
import logging
import json
from typing import List, Dict, Any, Optional, Union
import glob

from langchain_core.documents import Document

from config.settings import KNOWLEDGE_BASE_PATH
from app.core.vector_store import (
    product_vector_store,
    order_vector_store,
    return_refund_vector_store,
    general_vector_store,
    VectorStoreManager
)
from app.models.schemas import IntentType, DocumentInput
from app.utils.helpers import load_json_file, save_json_file

logger = logging.getLogger(__name__)


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
    
    def init_knowledge_base(self) -> Dict[str, bool]:
        """
        初始化知识库，加载所有知识文件
        
        Returns:
            各知识库初始化结果
        """
        results = {}
        
        try:
            # 加载产品信息到产品知识库
            product_files = glob.glob(os.path.join(self.knowledge_base_path, "product_*.json"))
            results["product_knowledge"] = self._load_files_to_vector_store(
                product_files, 
                self.vector_stores[IntentType.PRODUCT_INQUIRY]
            )
            
            # 加载订单信息到订单知识库
            order_files = glob.glob(os.path.join(self.knowledge_base_path, "order_*.json"))
            results["order_knowledge"] = self._load_files_to_vector_store(
                order_files, 
                self.vector_stores[IntentType.ORDER_STATUS]
            )
            
            # 加载退货退款信息到退货退款知识库
            return_files = glob.glob(os.path.join(self.knowledge_base_path, "*refund*.json"))
            results["return_refund_knowledge"] = self._load_files_to_vector_store(
                return_files, 
                self.vector_stores[IntentType.RETURN_REFUND]
            )
            
            # 加载常见问题到通用知识库
            faq_files = glob.glob(os.path.join(self.knowledge_base_path, "faq*.json"))
            results["general_knowledge"] = self._load_files_to_vector_store(
                faq_files, 
                self.vector_stores[IntentType.GENERAL_INQUIRY]
            )
            
            logger.info("知识库初始化完成")
            return results
            
        except Exception as e:
            logger.error(f"初始化知识库失败: {str(e)}")
            return {"error": False}
    
    def _load_files_to_vector_store(self, file_paths: List[str], vector_store: VectorStoreManager) -> bool:
        """
        将文件加载到向量存储
        
        Args:
            file_paths: 文件路径列表
            vector_store: 向量存储管理器
            
        Returns:
            是否成功加载
        """
        all_success = True
        
        for file_path in file_paths:
            try:
                logger.info(f"正在加载文件到向量存储: {file_path}")
                success = vector_store.import_from_json(file_path)
                if not success:
                    logger.warning(f"加载文件失败: {file_path}")
                    all_success = False
            except Exception as e:
                logger.error(f"加载文件 {file_path} 时发生错误: {str(e)}")
                all_success = False
        
        return all_success
    
    def add_document(self, document: DocumentInput, intent_type: IntentType) -> bool:
        """
        添加文档到知识库
        
        Args:
            document: 要添加的文档
            intent_type: 意图类型
            
        Returns:
            是否成功添加
        """
        try:
            vector_store = self.vector_stores.get(intent_type)
            if not vector_store:
                logger.error(f"未找到意图 {intent_type} 对应的向量存储")
                return False
            
            # 创建Document对象
            doc = Document(
                page_content=document.text,
                metadata=document.metadata
            )
            
            # 添加到向量存储
            return vector_store.add_documents([doc])
            
        except Exception as e:
            logger.error(f"添加文档到知识库失败: {str(e)}")
            return False
    
    def clear_knowledge_base(self, intent_type: Optional[IntentType] = None) -> Dict[str, bool]:
        """
        清空知识库
        
        Args:
            intent_type: 要清空的意图类型知识库，如果为None则清空所有
            
        Returns:
            清空结果
        """
        results = {}
        
        try:
            if intent_type:
                # 清空特定知识库
                vector_store = self.vector_stores.get(intent_type)
                if vector_store:
                    results[intent_type.value] = vector_store.clear()
                else:
                    results[intent_type.value] = False
            else:
                # 清空所有知识库
                for intent, vector_store in self.vector_stores.items():
                    results[intent.value] = vector_store.clear()
            
            return results
            
        except Exception as e:
            logger.error(f"清空知识库失败: {str(e)}")
            return {"error": False}
    
    def save_document_to_file(self, document: Dict[str, Any], file_name: str) -> bool:
        """
        保存文档到文件
        
        Args:
            document: 文档内容
            file_name: 文件名
            
        Returns:
            是否成功保存
        """
        file_path = os.path.join(self.knowledge_base_path, file_name)
        
        try:
            # 如果已存在同名文件，先加载原文件内容
            existing_data = []
            if os.path.exists(file_path):
                existing_data = load_json_file(file_path) or []
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
            
            # 添加新文档
            existing_data.append(document)
            
            # 保存到文件
            return save_json_file(existing_data, file_path)
            
        except Exception as e:
            logger.error(f"保存文档到文件失败: {str(e)}")
            return False
    
    def get_all_knowledge_files(self) -> List[str]:
        """
        获取所有知识文件
        
        Returns:
            知识文件路径列表
        """
        try:
            return glob.glob(os.path.join(self.knowledge_base_path, "*.json"))
        except Exception as e:
            logger.error(f"获取知识文件列表失败: {str(e)}")
            return []
    
    def get_knowledge_content(self, file_name: str) -> Optional[Any]:
        """
        获取知识文件内容
        
        Args:
            file_name: 文件名
            
        Returns:
            文件内容
        """
        file_path = os.path.join(self.knowledge_base_path, file_name)
        return load_json_file(file_path)


# 单例模式
knowledge_service = KnowledgeService() 