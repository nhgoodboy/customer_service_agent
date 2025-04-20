import requests
import json
import uuid

# 服务配置
API_BASE_URL = "http://localhost:8000/api"


def create_session():
    """创建会话"""
    response = requests.post(f"{API_BASE_URL}/session/create")
    if response.status_code == 200:
        session_id = response.json().get("session_id")
        print(f"创建会话成功，会话ID: {session_id}")
        return session_id
    else:
        print(f"创建会话失败: {response.text}")
        return None


def send_message(session_id, message):
    """发送消息"""
    data = {
        "query": message,
        "session_id": session_id
    }
    response = requests.post(f"{API_BASE_URL}/chat", json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"\n智能体回复: {result['response']}")
        print(f"识别意图: {result['intent']}")
        if result.get("sources"):
            print(f"信息来源: {', '.join(result['sources'])}")
        return result
    else:
        print(f"发送消息失败: {response.text}")
        return None


def get_history(session_id):
    """获取聊天历史"""
    response = requests.get(f"{API_BASE_URL}/session/{session_id}/history")
    if response.status_code == 200:
        history = response.json()
        print("\n聊天历史:")
        for msg in history:
            role = "用户" if msg["role"] == "user" else "智能体"
            print(f"{role}: {msg['content']}")
        return history
    else:
        print(f"获取聊天历史失败: {response.text}")
        return None


def clear_session(session_id):
    """清除会话"""
    response = requests.delete(f"{API_BASE_URL}/session/{session_id}")
    if response.status_code == 200:
        print(f"会话已清除")
        return True
    else:
        print(f"清除会话失败: {response.text}")
        return False


def interactive_chat():
    """交互式聊天"""
    print("=== 电商客服智能体示例 ===")
    print("输入'exit'退出，输入'clear'清除当前会话，输入'history'查看聊天历史")
    
    # 创建会话
    session_id = create_session()
    if not session_id:
        session_id = str(uuid.uuid4())
        print(f"使用本地生成的会话ID: {session_id}")
    
    while True:
        user_input = input("\n请输入您的问题: ")
        
        if user_input.lower() == 'exit':
            print("谢谢使用，再见！")
            break
        elif user_input.lower() == 'clear':
            clear_session(session_id)
            continue
        elif user_input.lower() == 'history':
            get_history(session_id)
            continue
        
        # 发送消息
        send_message(session_id, user_input)


def run_demo_script():
    """运行演示脚本"""
    print("=== 电商客服智能体演示 ===")
    
    # 创建会话
    session_id = create_session()
    if not session_id:
        return
    
    # 测试案例
    test_cases = [
        "这款星云智能手机X1的电池续航怎么样？",
        "我昨天下单的手机什么时候能到？",
        "我的订单号是OD2023112786302，能查一下物流状态吗？",
        "退货运费谁来承担？",
        "如果收到的产品有质量问题，该怎么申请退款？"
    ]
    
    # 依次发送消息
    for message in test_cases:
        print(f"\n用户: {message}")
        send_message(session_id, message)
    
    # 获取聊天历史
    get_history(session_id)


if __name__ == "__main__":
    choice = input("请选择运行模式：1. 交互式聊天  2. 演示脚本\n输入选择(1/2): ")
    
    if choice == "1":
        interactive_chat()
    elif choice == "2":
        run_demo_script()
    else:
        print("无效的选择，退出程序") 