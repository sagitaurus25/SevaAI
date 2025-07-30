let sessionId = generateSessionId();
let isConnected = false;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
    updateConnectionStatus('Connected', true);
});

function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

function initializeChat() {
    console.log('Chat initialized with session ID:', sessionId);
}

function setupEventListeners() {
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    
    // Enter key to send message
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Character counter
    messageInput.addEventListener('input', function() {
        const charCount = this.value.length;
        document.getElementById('charCount').textContent = charCount;
        
        if (charCount >= 450) {
            document.getElementById('charCount').style.color = '#dc3545';
        } else {
            document.getElementById('charCount').style.color = '#6c757d';
        }
    });
    
    // Auto-resize and focus
    messageInput.focus();
}

async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    
    // Disable input and show loading
    setLoading(true);
    messageInput.value = '';
    document.getElementById('charCount').textContent = '0';
    
    // Add user message to chat
    addMessage(message, 'user');
    
    try {
        // Send to backend
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId,
                user_id: 'demo_user'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add bot response to chat
        addMessage(data.response, 'bot');
        
        // Handle clarification if needed
        if (data.needs_clarification) {
            console.log('Clarification needed');
        }
        
    } catch (error) {
        console.error('Error sending message:', error);
        addMessage('Sorry, I encountered an error processing your request. Please make sure the backend is running and try again.', 'bot');
    } finally {
        setLoading(false);
        messageInput.focus();
    }
}

function addMessage(content, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Format the content (simple formatting for now)
    if (content.includes('\n')) {
        contentDiv.innerHTML = content.split('\n').map(line => {
            if (line.trim().startsWith('`') && line.trim().endsWith('`')) {
                return `<code>${line.trim().slice(1, -1)}</code>`;
            }
            return `<p>${escapeHtml(line)}</p>`;
        }).join('');
    } else {
        contentDiv.innerHTML = `<p>${escapeHtml(content)}</p>`;
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function quickAction(message) {
    const messageInput = document.getElementById('messageInput');
    messageInput.value = message;
    sendMessage();
}

function setLoading(loading) {
    const sendButton = document.getElementById('sendButton');
    const sendButtonText = document.getElementById('sendButtonText');
    const sendButtonSpinner = document.getElementById('sendButtonSpinner');
    const messageInput = document.getElementById('messageInput');
    
    if (loading) {
        sendButton.disabled = true;
        sendButtonText.style.display = 'none';
        sendButtonSpinner.style.display = 'inline';
        messageInput.disabled = true;
    } else {
        sendButton.disabled = false;
        sendButtonText.style.display = 'inline';
        sendButtonSpinner.style.display = 'none';
        messageInput.disabled = false;
    }
}

function updateConnectionStatus(status, connected) {
    const statusElement = document.getElementById('connectionStatus');
    statusElement.textContent = status;
    statusElement.className = connected ? 'status-connected' : 'status-disconnected';
    isConnected = connected;
}

// Test connection periodically
setInterval(async function() {
    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            if (!isConnected) {
                updateConnectionStatus('Connected', true);
            }
        } else {
            updateConnectionStatus('Disconnected', false);
        }
    } catch (error) {
        updateConnectionStatus('Disconnected', false);
    }
}, 10000); // Check every 10 seconds