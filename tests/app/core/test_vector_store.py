import unittest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest
from langchain_core.documents import Document

from app.core.vector_store import VectorStoreManager


class TestVectorStore:
    @pytest.fixture
    def vector_store(self):
        """创建测试用的向量存储"""
        # 使用Mock替代真实的嵌入模型和Chroma客户端
        with patch("app.core.vector_store.HuggingFaceEmbeddings") as mock_embeddings, \
             patch("app.core.vector_store.Chroma") as mock_chroma:
            # 配置模拟的嵌入模型
            mock_embeddings.return_value = MagicMock()
            # 配置模拟的Chroma客户端
            mock_chroma.return_value = MagicMock()
            
            # 创建向量存储管理器
            manager = VectorStoreManager(collection_name="test_collection")
            yield manager
    
    def test_enrich_document_with_context(self, vector_store):
        """测试文档上下文增强功能"""
        # 测试FAQ文档，应该保持原样
        doc1 = Document(
            page_content='{"question": "测试问题?", "answer": "测试回答"}',
            metadata={"type": "faq"}
        )
        enriched_doc1 = vector_store._enrich_document_with_context(doc1)
        assert enriched_doc1.page_content == doc1.page_content
        assert enriched_doc1.metadata == doc1.metadata
        
        # 测试普通JSON文档，应该进行增强
        doc2 = Document(
            page_content='{"name": "测试产品", "price": 100}',
            metadata={"source": "test.json"}
        )
        enriched_doc2 = vector_store._enrich_document_with_context(doc2)
        assert "name: 测试产品" in enriched_doc2.page_content
        assert "price: 100" in enriched_doc2.page_content
        assert "原始数据" in enriched_doc2.page_content
        
        # 测试非JSON文档，应该保持原样
        doc3 = Document(
            page_content="普通文本内容",
            metadata={"source": "test.txt"}
        )
        enriched_doc3 = vector_store._enrich_document_with_context(doc3)
        assert enriched_doc3.page_content == doc3.page_content
        assert enriched_doc3.metadata == doc3.metadata
    
    def test_create_enhanced_query(self, vector_store):
        """测试查询增强功能"""
        # 测试短查询中的积分关键词
        query1 = "如何使用积分"
        enhanced1 = vector_store._create_enhanced_query(query1)
        assert "积分" in enhanced1
        assert len(enhanced1) > len(query1)
        assert "购物积分" in enhanced1
        
        # 测试短查询中的订单关键词
        query2 = "订单在哪里查询"
        enhanced2 = vector_store._create_enhanced_query(query2)
        assert "订单" in enhanced2
        assert len(enhanced2) > len(query2)
        assert "物流" in enhanced2
        
        # 测试长查询应保持不变
        query3 = "这是一个很长的查询文本，超过了十个字符，不应该被增强处理，应该保持原样返回"
        enhanced3 = vector_store._create_enhanced_query(query3)
        assert enhanced3 == query3
    
    @patch("app.core.vector_store.json.loads")
    def test_enrich_document_error_handling(self, mock_json_loads, vector_store):
        """测试文档增强的错误处理"""
        # 模拟JSON解析错误
        mock_json_loads.side_effect = json.JSONDecodeError("测试错误", "", 0)
        
        # 创建一个含有JSON格式内容的文档
        doc = Document(
            page_content='{"invalid": "json",}',  # 故意使用无效的JSON
            metadata={"source": "test.json"}
        )
        
        # 调用方法
        result = vector_store._enrich_document_with_context(doc)
        
        # 验证结果是原始文档
        assert result.page_content == doc.page_content
        assert result.metadata == doc.metadata
    
    @patch("app.core.vector_store.Chroma")
    def test_add_documents(self, mock_chroma, vector_store):
        """测试添加文档功能"""
        # 创建不同类型的文档
        docs = [
            Document(page_content="测试文档1", metadata={"source": "test1"}),
            {"text": "测试文档2", "metadata": {"source": "test2"}},
            "纯文本文档"
        ]
        
        # 模拟文本分块器
        vector_store.text_splitter.split_documents = MagicMock(return_value=[
            Document(page_content="分块1", metadata={}),
            Document(page_content="分块2", metadata={})
        ])
        
        # 调用方法
        result = vector_store.add_documents(docs)
        
        # 验证结果
        assert result is True
        # 验证Chroma的add_documents被调用
        vector_store.vector_store.add_documents.assert_called_once()
    
    @patch("app.core.vector_store.Chroma")
    def test_similarity_search(self, mock_chroma, vector_store):
        """测试相似度搜索功能"""
        # 模拟Chroma的similarity_search返回结果
        vector_store.vector_store.similarity_search.return_value = [
            Document(page_content="相似文档1", metadata={"source": "test1"}),
            Document(page_content="相似文档2", metadata={"source": "test2"})
        ]
        
        # 模拟_create_enhanced_query方法
        vector_store._create_enhanced_query = MagicMock(return_value="增强的查询")
        
        # 调用方法
        result = vector_store.get_relevant_documents("测试查询")
        
        # 验证结果
        assert len(result) == 2
        assert result[0].page_content == "相似文档1"
        assert result[1].page_content == "相似文档2"
        
        # 验证方法调用
        vector_store._create_enhanced_query.assert_called_once_with("测试查询")
        vector_store.vector_store.similarity_search.assert_called_once_with("增强的查询", k=5)
    
    def test_import_from_json(self, vector_store):
        """测试从JSON文件导入数据"""
        # 创建临时JSON文件
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w', encoding='utf-8') as temp:
            test_data = [
                {"id": 1, "question": "测试问题1?", "answer": "测试回答1"},
                {"id": 2, "question": "测试问题2?", "answer": "测试回答2"}
            ]
            json.dump(test_data, temp)
            temp_path = temp.name
        
        try:
            # 模拟add_documents方法
            vector_store.add_documents = MagicMock(return_value=True)
            
            # 调用方法
            result = vector_store.import_from_json(temp_path)
            
            # 验证结果
            assert result is True
            
            # 验证add_documents被调用
            vector_store.add_documents.assert_called_once()
            # 获取传递给add_documents的参数
            args, _ = vector_store.add_documents.call_args
            documents = args[0]
            # 验证创建了正确数量的文档
            assert len(documents) == 2
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path) 