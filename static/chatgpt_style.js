const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const messagesContainer = document.getElementById('messagesContainer');
const messagesList = document.getElementById('messagesList');
const welcomeScreen = document.getElementById('welcomeScreen');
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('mainContent');

// Auto-resize textarea
userInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 200) + 'px';
    
    sendBtn.disabled = this.value.trim() === '';
});

userInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (this.value.trim()) {
            chatForm.dispatchEvent(new Event('submit'));
        }
    }
});

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const question = userInput.value.trim();
    if (!question) return;
    
    // Hide welcome screen
    welcomeScreen.style.display = 'none';
    messagesList.style.display = 'block';
    
    // Add user message
    addMessage(question, 'user');
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.disabled = true;
    
    // Add typing indicator
    const typingId = addTypingIndicator();
    
    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question })
        });
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const data = await response.json();
        removeTypingIndicator(typingId);
        
        const answer = data.answer || data.response || data.result || 'No response';
        addMessage(typeof answer === 'string' ? answer : JSON.stringify(answer), 'assistant');
    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
        console.error('Error:', error);
    }
});

function addMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    
    if (type === 'assistant') {
        avatar.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M9 1.5L1.5 5.25L9 9L16.5 5.25L9 1.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                <path d="M1.5 12.75L9 16.5L16.5 12.75" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                <path d="M1.5 9L9 12.75L16.5 9" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            </svg>
        `;
    } else {
        avatar.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M15 15.75v-1.5a3 3 0 00-3-3H6a3 3 0 00-3 3v1.5M12 5.25a3 3 0 11-6 0 3 3 0 016 0z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
    }
    
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    messageText.textContent = text;
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(messageText);
    messageDiv.appendChild(wrapper);
    messagesList.appendChild(messageDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = 'typing-' + Date.now();
    
    const wrapper = document.createElement('div');
    wrapper.className = 'message-content-wrapper';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = `
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 1.5L1.5 5.25L9 9L16.5 5.25L9 1.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M1.5 12.75L9 16.5L16.5 12.75" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
            <path d="M1.5 9L9 12.75L16.5 9" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>
    `;
    
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    messageText.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    
    wrapper.appendChild(avatar);
    wrapper.appendChild(messageText);
    messageDiv.appendChild(wrapper);
    messagesList.appendChild(messageDiv);
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return messageDiv.id;
}

function removeTypingIndicator(id) {
    const typingDiv = document.getElementById(id);
    if (typingDiv) {
        typingDiv.remove();
    }
}

function toggleSidebar() {
    sidebar.classList.toggle('collapsed');
}

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

function newChat() {
    messagesList.innerHTML = '';
    messagesList.style.display = 'none';
    welcomeScreen.style.display = 'flex';
    userInput.value = '';
    userInput.style.height = 'auto';
    sendBtn.disabled = true;
}

// Load theme from localStorage
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
});
