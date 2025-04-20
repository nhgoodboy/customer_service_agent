document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const chatMessages = document.querySelector('.chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.querySelector('.send-btn');
    const newChatButton = document.getElementById('new-chat-btn');
    const clearHistoryButton = document.getElementById('clear-history-btn');
    const chatList = document.querySelector('.chat-list');
    const sidebar = document.querySelector('.sidebar');
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    
    // 移动设备菜单按钮
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
        
        // 点击聊天区域时关闭菜单
        document.querySelector('.chat-container').addEventListener('click', function(e) {
            if (sidebar.classList.contains('active') && !e.target.closest('#mobile-menu-btn')) {
                sidebar.classList.remove('active');
            }
        });
    }
    
    // 移除欢迎消息
    const welcomeMessage = document.querySelector('.welcome-message');
    if (welcomeMessage) {
        chatMessages.removeChild(welcomeMessage);
    }
    
    // 状态变量
    let currentChatId = null;
    let chatHistory = [];
    
    // 初始化
    initApp();
    
    // 事件监听器
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    newChatButton.addEventListener('click', createNewChat);
    clearHistoryButton.addEventListener('click', clearHistory);
    
    // 初始化应用
    function initApp() {
        // 从本地存储加载聊天历史
        loadChatHistory();
        
        // 如果没有聊天记录，创建一个新的
        if (chatHistory.length === 0) {
            createNewChat();
        } else {
            // 加载最近的聊天
            loadChat(chatHistory[0].id);
        }
        
        // 更新聊天列表UI
        updateChatList();
    }
    
    // 创建新聊天
    function createNewChat() {
        const chatId = 'chat_' + Date.now();
        const newChat = {
            id: chatId,
            title: '新对话',
            messages: []
        };
        
        // 添加到聊天历史
        chatHistory.unshift(newChat);
        saveChatHistory();
        
        // 更新UI
        loadChat(chatId);
        updateChatList();
    }
    
    // 加载指定的聊天
    function loadChat(chatId) {
        currentChatId = chatId;
        
        // 查找当前聊天
        const currentChat = chatHistory.find(chat => chat.id === chatId);
        if (!currentChat) return;
        
        // 清空聊天区域
        chatMessages.innerHTML = '';
        
        // 加载消息
        currentChat.messages.forEach(msg => {
            appendMessage(msg.content, msg.sender, msg.timestamp);
        });
        
        // 更新聊天列表中的活动状态
        updateActiveChat();
        
        // 滚动到底部
        scrollToBottom();
    }
    
    // 发送消息
    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        
        // 清空输入框
        chatInput.value = '';
        
        // 获取当前聊天
        const currentChat = chatHistory.find(chat => chat.id === currentChatId);
        if (!currentChat) return;
        
        // 添加用户消息到界面
        const timestamp = new Date().toISOString();
        appendMessage(message, 'user', timestamp);
        
        // 保存消息到聊天历史
        currentChat.messages.push({
            content: message,
            sender: 'user',
            timestamp: timestamp
        });
        
        // 如果这是第一条消息，更新聊天标题
        if (currentChat.messages.length === 1) {
            currentChat.title = message.length > 30 ? message.substring(0, 30) + '...' : message;
            updateChatList();
        }
        
        // 保存聊天历史
        saveChatHistory();
        
        // 滚动到底部
        scrollToBottom();
        
        // 发送到服务器并获取回复
        sendToServer(message);
    }
    
    // 发送消息到服务器
    function sendToServer(message) {
        // 添加加载指示器
        const loadingElement = document.createElement('div');
        loadingElement.className = 'message bot-message';
        loadingElement.innerHTML = '<span class="loading"></span>正在思考...';
        chatMessages.appendChild(loadingElement);
        scrollToBottom();
        
        // 查找或创建session_id
        let sessionId = localStorage.getItem('session_id');
        
        // 确保sessionId不是"undefined"字符串
        if (sessionId === "undefined" || sessionId === null || sessionId === undefined) {
            sessionId = null;
        }
        
        // 如果没有session_id，先创建一个
        const createSessionIfNeeded = !sessionId 
            ? fetch('/api/session/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
              }).then(res => res.json()).then(data => {
                sessionId = data.session_id;
                localStorage.setItem('session_id', sessionId);
                console.log('创建新会话ID:', sessionId);
                return sessionId;
              })
            : Promise.resolve(sessionId);
        
        createSessionIfNeeded
            .then(sessionId => {
                console.log('使用会话ID:', sessionId);
                // 发送API请求
                return fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        query: message,
                        session_id: sessionId
                    })
                });
            })
            .then(response => {
                if (!response.ok) {
                    if (response.status === 404) {
                        throw new Error('接口未找到，请确认服务器是否正常运行');
                    } else if (response.status === 422) {
                        throw new Error('请求参数格式错误，请检查API格式要求');
                    } else {
                        return response.json().then(errorData => {
                            throw new Error(`${response.statusText}: ${errorData.detail || errorData.message || '未知错误'}`);
                        }).catch(() => {
                            throw new Error(`请求失败: ${response.status} ${response.statusText}`);
                        });
                    }
                }
                return response.json();
            })
            .then(data => {
                // 移除加载指示器
                if (loadingElement.parentNode) {
                    chatMessages.removeChild(loadingElement);
                }
                
                // 添加机器人回复
                const timestamp = new Date().toISOString();
                
                // 处理回复内容，添加源信息
                let formattedResponse = data.response;
                if (data.sources && data.sources.length > 0) {
                    formattedResponse += `<div class="sources">
                        <p>参考源: ${data.sources.join(', ')}</p>
                    </div>`;
                }
                
                appendMessage(formattedResponse, 'bot', timestamp);
                
                // 保存回复到聊天历史
                const currentChat = chatHistory.find(chat => chat.id === currentChatId);
                if (currentChat) {
                    currentChat.messages.push({
                        content: formattedResponse,
                        sender: 'bot',
                        timestamp: timestamp
                    });
                    saveChatHistory();
                }
                
                // 滚动到底部
                scrollToBottom();
            })
            .catch(error => {
                console.error('Error:', error);
                
                // 移除加载指示器
                if (loadingElement.parentNode) {
                    chatMessages.removeChild(loadingElement);
                }
                
                // 显示错误信息
                const errorElement = document.createElement('div');
                errorElement.className = 'error-message';
                errorElement.textContent = '发生错误: ' + error.message;
                chatMessages.appendChild(errorElement);
                
                // 滚动到底部
                scrollToBottom();
            });
    }
    
    // 添加消息到聊天区域
    function appendMessage(content, sender, timestamp) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
        
        // 设置消息内容
        messageElement.innerHTML = `
            ${content}
            <span class="message-time">${formatTimestamp(timestamp)}</span>
        `;
        
        // 添加到聊天区域
        chatMessages.appendChild(messageElement);
    }
    
    // 更新聊天列表UI
    function updateChatList() {
        chatList.innerHTML = '';
        
        chatHistory.forEach(chat => {
            const chatElement = document.createElement('div');
            chatElement.className = 'chat-item';
            chatElement.dataset.id = chat.id;
            
            chatElement.innerHTML = `
                <div class="chat-title">${chat.title}</div>
                <button class="delete-chat"><i class="fas fa-times"></i></button>
            `;
            
            // 点击聊天项加载对应聊天
            chatElement.addEventListener('click', function(e) {
                if (!e.target.closest('.delete-chat')) {
                    loadChat(chat.id);
                }
            });
            
            // 删除聊天
            const deleteBtn = chatElement.querySelector('.delete-chat');
            deleteBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                deleteChat(chat.id);
            });
            
            chatList.appendChild(chatElement);
        });
        
        updateActiveChat();
    }
    
    // 更新活动聊天的样式
    function updateActiveChat() {
        document.querySelectorAll('.chat-item').forEach(item => {
            if (item.dataset.id === currentChatId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    // 删除聊天
    function deleteChat(chatId) {
        // 过滤掉要删除的聊天
        chatHistory = chatHistory.filter(chat => chat.id !== chatId);
        
        // 如果删除的是当前聊天，加载另一个聊天
        if (chatId === currentChatId) {
            if (chatHistory.length > 0) {
                loadChat(chatHistory[0].id);
            } else {
                // 如果没有聊天了，创建一个新的
                createNewChat();
            }
        }
        
        // 保存并更新UI
        saveChatHistory();
        updateChatList();
    }
    
    // 清空所有聊天历史
    function clearHistory() {
        if (confirm('确定要清除所有聊天记录吗？此操作不可撤销。')) {
            chatHistory = [];
            localStorage.removeItem('chatHistory');
            createNewChat();
        }
    }
    
    // 加载聊天历史
    function loadChatHistory() {
        const saved = localStorage.getItem('chatHistory');
        if (saved) {
            try {
                chatHistory = JSON.parse(saved);
            } catch (e) {
                console.error('加载聊天历史失败:', e);
                chatHistory = [];
            }
        } else {
            chatHistory = [];
        }
    }
    
    // 保存聊天历史到本地存储
    function saveChatHistory() {
        try {
            localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
        } catch (e) {
            console.error('保存聊天历史失败:', e);
            
            // 如果存储空间不足，可能需要清理一些旧的聊天
            if (e.name === 'QuotaExceededError') {
                alert('本地存储空间不足，部分聊天历史可能无法保存。');
                
                // 可以考虑只保留最近的几个聊天
                if (chatHistory.length > 5) {
                    chatHistory = chatHistory.slice(0, 5);
                    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
                }
            }
        }
    }
    
    // 格式化时间戳为友好格式
    function formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    // 滚动到底部
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}); 