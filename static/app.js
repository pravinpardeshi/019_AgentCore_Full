const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const messagesDiv = document.getElementById('messages');
const sendButton = document.getElementById('sendButton');
const sourcesPanel = document.getElementById('sourcesPanel');
const sourcesList = document.getElementById('sourcesList');

// Configure AgentCore endpoint
const AGENTCORE_ENDPOINT = window.AGENTCORE_ENDPOINT || '/api/query';
const USE_AGENTCORE = window.USE_AGENTCORE === true || false;

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const question = userInput.value.trim();
    if (!question) return;
    
    // Add user message
    addMessage(question, 'user');
    userInput.value = '';
    sendButton.disabled = true;
    
    // Show typing indicator
    const typingId = showTypingIndicator();
    
    try {
        let response;
        if (USE_AGENTCORE && AGENTCORE_ENDPOINT !== '/api/query') {
            // Call AgentCore endpoint directly
            response = await fetch(`${AGENTCORE_ENDPOINT}/invocations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: question, inputText: question })
            });
        } else {
            // Call local backend
            response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question })
            });
        }
        
        if (!response.ok) {
            throw new Error('Failed to get response');
        }
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        // Handle different response formats
        const answer = data.answer || data.response || data.result || data.output || 'No response';
        const sources = data.sources || [];
        
        // Add assistant message
        addMessage(typeof answer === 'string' ? answer : JSON.stringify(answer), 'assistant');
        
        // Show sources if available
        if (sources && sources.length > 0) {
            showSources(sources);
        } else {
            sourcesPanel.style.display = 'none';
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
        console.error('Error:', error);
    } finally {
        sendButton.disabled = false;
        userInput.focus();
    }
});
