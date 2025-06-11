// Patient Portal JavaScript Functions

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) {
        alert('Please enter a message');
        return;
    }
    
    // Show typing indicator
    showTypingIndicator();
    
    // Add user message to chat
    addMessageToChat('user', message);
    input.value = '';
    resetTextareaHeight();
    
    try {
        const response = await fetch('/api/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });
        
        const result = await response.json();
        
        if (result.success && result.response && result.response.messages) {
            // Get clean assistant messages
            const assistantMessages = result.response.messages.filter(msg => 
                msg.message_type === 'assistant_message' && 
                msg.content && 
                msg.content.trim() !== ''
            );
            
            if (assistantMessages.length > 0) {
                // Use the last clean assistant message
                const lastMessage = assistantMessages[assistantMessages.length - 1];
                let content = lastMessage.content || 'Response received';
                
                // Clean up the content
                content = content.replace(/\*\*Assistant:\*\*/g, '').trim();
                
                addMessageToChat('assistant', content);
            } else {
                addMessageToChat('assistant', 'I received your message. How can I help you today?');
            }
        } else if (result.error) {
            addMessageToChat('assistant', `I'm sorry, I encountered an error: ${result.error}`);
        } else {
            addMessageToChat('assistant', 'I apologize, but I\'m having trouble responding right now. Please try again in a moment.');
        }
    } catch (error) {
        console.error('Error:', error);
        addMessageToChat('assistant', 'I\'m having trouble connecting. Please check your internet connection and try again.');
    } finally {
        hideTypingIndicator();
    }
}

function quickMessage(message) {
    const input = document.getElementById('messageInput');
    input.value = message;
    autoResizeTextarea(input);
    // Optionally send immediately or let user review and send
    sendMessage();
}

function addMessageToChat(role, text) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    let messageContent = '';
    if (role === 'user') {
        messageContent = `<strong>You:</strong> ${escapeHtml(text)}`;
    } else if (role === 'nurse') {
        messageContent = `<strong style="color: #2c5aa0;">${escapeHtml(text)}</strong>`;
    } else {
        messageContent = `<strong>Assistant:</strong> ${escapeHtml(text)}`;
    }
    
    messageDiv.innerHTML = `<div class="message-content">${messageContent}</div>`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Add animation
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateY(20px)';
    setTimeout(() => {
        messageDiv.style.transition = 'all 0.3s ease';
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    }, 10);
}

function showTypingIndicator() {
    document.getElementById('chatStatus').style.display = 'block';
    
    // Add typing animation to the status
    const status = document.getElementById('chatStatus');
    let dots = 0;
    const interval = setInterval(() => {
        dots = (dots + 1) % 4;
        status.innerHTML = `<em>Assistant is typing${'.'.repeat(dots)}</em>`;
    }, 500);
    
    // Store interval ID for cleanup
    status.dataset.interval = interval;
}

function hideTypingIndicator() {
    const status = document.getElementById('chatStatus');
    status.style.display = 'none';
    
    // Clear typing animation interval
    if (status.dataset.interval) {
        clearInterval(status.dataset.interval);
        delete status.dataset.interval;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function resetTextareaHeight() {
    const textarea = document.getElementById('messageInput');
    textarea.style.height = '60px';
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    
    // Allow Enter key to send message (Shift+Enter for new line)
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        autoResizeTextarea(this);
    });
    
    // Auto-scroll to bottom on page load
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Focus on message input
    messageInput.focus();
});

// Additional utility functions for enhanced UX
function copyMessageToClipboard(messageElement) {
    const text = messageElement.textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Message copied to clipboard');
    }).catch(() => {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showToast('Message copied to clipboard');
    });
}

function showToast(message, duration = 3000) {
    // Create toast notification
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #2c5aa0;
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        z-index: 1000;
        font-size: 14px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 10);
    
    // Remove after duration
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, duration);
}

// Handle offline/online status
window.addEventListener('online', function() {
    showToast('Connection restored');
});

window.addEventListener('offline', function() {
    showToast('Connection lost. Please check your internet connection.', 5011);
});