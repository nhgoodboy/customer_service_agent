// 在文件开头添加调试模式开关
const DEBUG_MODE = false; // 设置为true以显示会话调试信息

document.addEventListener('DOMContentLoaded', function() {
    // DOM元素
    const chatMessages = document.querySelector('.chat-messages');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.querySelector('.send-btn');
    const chatList = document.querySelector('.chat-list');
    const newChatButton = document.getElementById('new-chat-btn');
    const clearHistoryButton = document.getElementById('clear-history-btn');
    const mobileMenuButton = document.getElementById('mobile-menu-btn');
    
    // 用户聊天记录
    let chatHistory = [];
    let currentChatId = null;
    
    // 初始化应用
    initApp();
    
    // 初始化应用程序
    function initApp() {
        // 加载聊天历史
        loadChatHistory();
        
        // 如果没有聊天记录，创建一个新的
        if (chatHistory.length === 0) {
            createNewChat();
        } else {
            // 加载最近的聊天
            loadChat(chatHistory[0].id);
        }
        
        // 更新聊天列表
        updateChatList();
        
        // 事件监听器
        sendButton.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        newChatButton.addEventListener('click', createNewChat);
        clearHistoryButton.addEventListener('click', clearHistory);
        
        // 移动设备菜单
        mobileMenuButton.addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('active');
        });
        
        // 处理会话调试模式
        if (DEBUG_MODE) {
            const sessionInfo = document.querySelector('.session-info');
            sessionInfo.style.display = 'block';
            
            // 添加会话刷新按钮处理程序
            document.getElementById('refresh-session-btn').addEventListener('click', refreshSessionInfo);
            
            // 初始化显示会话信息
            refreshSessionInfo();
        }
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
        
        // 获取会话创建时间，检查是否过期
        const sessionCreatedAt = localStorage.getItem('session_created_at');
        const now = Date.now();
        // 如果会话创建时间超过60分钟，视为过期
        const SESSION_TIMEOUT = 60 * 60 * 1000; // 60分钟，单位毫秒
        if (sessionCreatedAt && (now - parseInt(sessionCreatedAt)) > SESSION_TIMEOUT) {
            console.log('会话已过期，创建新会话');
            sessionId = null;
            localStorage.removeItem('session_id');
            localStorage.removeItem('session_created_at');
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
                localStorage.setItem('session_created_at', Date.now().toString());
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
                
                // 更新会话活跃时间
                localStorage.setItem('session_created_at', Date.now().toString());
                
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
            // 清除会话ID和相关数据
            localStorage.removeItem('session_id');
            localStorage.removeItem('session_created_at');
            console.log('已清除所有聊天记录和会话数据');
            createNewChat();
            updateChatList();
            
            // 调用API清除服务端会话
            const oldSessionId = localStorage.getItem('session_id');
            if (oldSessionId) {
                fetch(`/api/session/${oldSessionId}`, {
                    method: 'DELETE'
                }).then(response => {
                    console.log('服务端会话已清除');
                }).catch(error => {
                    console.error('清除服务端会话失败:', error);
                });
            }
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
    
    // 刷新会话信息（仅在调试模式下使用）
    function refreshSessionInfo() {
        const sessionId = localStorage.getItem('session_id');
        const sessionCreatedAt = localStorage.getItem('session_created_at');
        const sessionStatusEl = document.getElementById('session-status');
        
        if (sessionId) {
            const createdDate = sessionCreatedAt ? new Date(parseInt(sessionCreatedAt)) : 'unknown';
            sessionStatusEl.innerHTML = `会话ID: ${sessionId}<br>创建时间: ${createdDate}<br>`;
            
            // 从服务器获取会话上下文信息
            fetch(`/api/session/${sessionId}/context`)
                .then(res => res.json())
                .then(data => {
                    sessionStatusEl.innerHTML += `消息数: ${data.message_count}<br>最后活跃: ${new Date(data.last_active * 1000).toLocaleString()}`;
                })
                .catch(err => {
                    sessionStatusEl.innerHTML += `<span style="color:red">获取会话信息失败: ${err.message}</span>`;
                });
        } else {
            sessionStatusEl.textContent = '无有效会话';
        }
    }
}); 