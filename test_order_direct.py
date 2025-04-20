#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单的订单查询测试程序
此程序直接读取订单数据，不依赖应用程序代码
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_order_direct")

# 获取当前脚本所在目录
CURRENT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_PATH = os.path.join(CURRENT_DIR, "data", "knowledge_base")

def generate_order_response(order_info):
    """根据订单信息生成响应"""
    order_id = order_info.get("order_id", "未知")
    status = order_info.get("status", "未知").lower()
    
    # 状态映射到中文
    status_map = {
        "shipped": "已发货",
        "delivered": "已送达",
        "processing": "处理中",
        "cancelled": "已取消",
        "pending": "待确认"
    }
    
    status_cn = status_map.get(status, status)
    
    # 生成响应文本，确保中文引号被正确转义
    response = f"您的订单 {order_id} 状态为: \"{status_cn}\"。"
    
    # 添加预计送达时间
    if "estimated_delivery" in order_info:
        response += f" 预计送达时间为 {order_info['estimated_delivery']}。"
    
    # 添加物流信息
    if "tracking_number" in order_info:
        tracking = order_info["tracking_number"]
        carrier = order_info.get("carrier", "物流公司")
        response += f" 物流公司: {carrier}, 物流单号: {tracking}。"
    
    # 添加订单商品信息
    if "items" in order_info and order_info["items"]:
        items = order_info["items"]
        if len(items) == 1:
            item = items[0]
            response += f"\n\n您购买的商品是: {item.get('name')} x {item.get('quantity')}。"
        else:
            items_text = ", ".join([f"{item.get('name')} x {item.get('quantity')}" for item in items[:3]])
            if len(items) > 3:
                items_text += f" 等共 {len(items)} 件商品"
            response += f"\n\n您购买的商品包括: {items_text}。"
    
    # 添加友好结尾
    response += "\n\n如果您有其他问题，随时告诉我。"
    
    return response

async def test_order_query():
    """测试订单查询功能"""
    logger.info("开始测试订单查询...")
    
    # 直接读取订单信息
    order_id = "OD2023110512567"
    logger.info(f"查询订单ID: {order_id}")
    
    # 1. 读取订单文件
    order_file = os.path.join(KNOWLEDGE_BASE_PATH, "order_samples.json")
    if not os.path.exists(order_file):
        logger.error(f"订单文件不存在: {order_file}")
        return
    
    try:
        with open(order_file, 'r', encoding='utf-8') as f:
            orders = json.load(f)
        
        logger.info(f"成功读取订单文件，包含 {len(orders)} 条订单记录")
        
        # 2. 搜索特定订单ID
        order = next((o for o in orders if o.get("order_id") == order_id), None)
        
        if order:
            logger.info("订单查询成功!")
            logger.info(f"订单ID: {order.get('order_id')}")
            logger.info(f"订单状态: {order.get('status')}")
            logger.info(f"创建时间: {order.get('order_date')}")
            if 'estimated_delivery' in order:
                logger.info(f"预计送达: {order.get('estimated_delivery')}")
            if 'items' in order:
                logger.info(f"订单商品: {len(order.get('items'))} 件")
                for item in order.get('items'):
                    logger.info(f"  - {item.get('name')} x {item.get('quantity')} (价格: {item.get('price')})")
            
            # 3. 生成订单查询回复
            response = generate_order_response(order)
            logger.info(f"\n订单查询回复:\n{response}")
        else:
            logger.error(f"未找到订单ID: {order_id}")
            
    except Exception as e:
        logger.error(f"订单查询出错: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    print(f"Python版本: {sys.version}")
    asyncio.run(test_order_query())

if __name__ == "__main__":
    main() 