import os
import sys
import requests
import json
import glob

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.knowledge_service import knowledge_service


def init_knowledge_base_api():
    """使用API初始化知识库"""
    print("=== 通过API初始化知识库 ===")
    
    # API配置
    API_BASE_URL = "http://localhost:8000/api"
    
    try:
        # 调用初始化接口
        response = requests.post(f"{API_BASE_URL}/knowledge/init")
        
        if response.status_code == 200:
            results = response.json()
            print("知识库初始化成功:")
            print(json.dumps(results, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"知识库初始化失败: {response.text}")
            return False
    except Exception as e:
        print(f"API调用出错: {str(e)}")
        return False


def init_knowledge_base_local():
    """本地直接初始化知识库"""
    print("=== 本地直接初始化知识库 ===")
    
    try:
        # 调用知识服务的初始化方法
        results = knowledge_service.init_knowledge_base()
        
        print("知识库初始化结果:")
        for kb_name, success in results.items():
            print(f"- {kb_name}: {'成功' if success else '失败'}")
        
        return all(results.values())
    except Exception as e:
        print(f"初始化失败: {str(e)}")
        return False


def list_knowledge_files():
    """列出知识库文件"""
    print("\n=== 知识库文件列表 ===")
    
    try:
        # 使用知识服务获取文件列表
        files = knowledge_service.get_all_knowledge_files()
        
        if files:
            for i, file_path in enumerate(files, 1):
                file_name = os.path.basename(file_path)
                print(f"{i}. {file_name}")
        else:
            print("未找到知识库文件")
            
    except Exception as e:
        print(f"获取文件列表失败: {str(e)}")


if __name__ == "__main__":
    choice = input("请选择初始化方式：1. 通过API  2. 本地直接初始化\n输入选择(1/2): ")
    
    success = False
    if choice == "1":
        success = init_knowledge_base_api()
    elif choice == "2":
        success = init_knowledge_base_local()
    else:
        print("无效的选择，退出程序")
        sys.exit(1)
    
    if success:
        list_knowledge_files()
        print("\n知识库初始化完成!")
    else:
        print("\n知识库初始化失败!") 