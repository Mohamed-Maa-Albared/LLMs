const form = document.getElementById("prompt-form");
const conversationHistory = document.getElementById("conversation-history");
const conversationList = document.getElementById("conversation-list");
const newConversationBtn = document.getElementById("new-conversation-btn");
const darkModeToggle = document.getElementById("dark-mode-toggle");
let isTyping = false;
let conversations = [];
let currentConversationId = null;

newConversationBtn.addEventListener("click", startNewConversation);

// Dark mode toggle functionality
if (localStorage.getItem('dark-mode') === 'enabled') {
    document.body.classList.add('dark-mode');
    darkModeToggle.textContent = 'Light Mode';
} else {
    darkModeToggle.textContent = 'Dark Mode';
}

darkModeToggle.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');

    // Save the user's preference in localStorage
    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('dark-mode', 'enabled');
        darkModeToggle.textContent = 'Light Mode';
    } else {
        localStorage.setItem('dark-mode', 'disabled');
        darkModeToggle.textContent = 'Dark Mode';
    }
});

function startNewConversation() {
    const newConversation = {
        id: Date.now(),
        name: `Conversation ${conversations.length + 1}`,
        messages: []
    };
    conversations.push(newConversation);
    currentConversationId = newConversation.id;
    updateConversationList();
    clearConversationHistory();
}

function updateConversationList() {
    conversationList.innerHTML = '';
    conversations.forEach(conv => {
        const li = document.createElement("li");
        li.innerHTML = `
            <span class="conversation-name" contenteditable="true">${conv.name}</span>
            <div>
                <button class="delete-btn">Delete</button>
            </div>
        `;
        li.querySelector('.conversation-name').addEventListener('input', (e) => {
            e.stopPropagation();
            conv.name = e.target.textContent;
        });
        li.querySelector('.delete-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id);
        });
        li.addEventListener("click", () => loadConversation(conv.id));
        conversationList.appendChild(li);
    });
}

function deleteConversation(id) {
    if (confirm("Are you sure you want to delete this conversation?")) {
        conversations = conversations.filter(conv => conv.id !== id);
        if (currentConversationId === id) {
            currentConversationId = null;
            clearConversationHistory();
        }
        updateConversationList();
    }
}

function loadConversation(id) {
    currentConversationId = id;
    clearConversationHistory();
    const conversation = conversations.find(conv => conv.id === id);
    conversation.messages.forEach(msg => addToConversationHistory(msg.speaker, msg.content));
}

function clearConversationHistory() {
    conversationHistory.innerHTML = '';
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (isTyping) return;

    const promptInput = document.getElementById("prompt");
    const prompt = promptInput.value.trim();
    promptInput.value = "";

    if (prompt === "") return;

    addToConversationHistory("You", prompt);

    // Get the toggle value
    const includeHistory = document.getElementById("include-history").checked;

    // Prepare the prompt to send
    let promptToSend;
    if (includeHistory && currentConversationId) {
        const conversation = conversations.find(conv => conv.id === currentConversationId);
        // Build the conversation history as a single string
        promptToSend = conversation.messages.map(msg => `${msg.speaker}: ${msg.content}`).join('\n');
    } else {
        promptToSend = `You: ${prompt}`;
    }

    // Create the payload
    const payload = {
        prompt: promptToSend
    };

    const responseLi = document.createElement("li");
    responseLi.innerHTML = `
        <div class="message-header">
            <strong>LLaMA:</strong>
            <button class="collapse-btn">Collapse</button>
        </div>
        <div class="message-content"><span class="typing">LLaMA is thinking</span></div>
    `;
    conversationHistory.appendChild(responseLi);
    conversationHistory.scrollTop = conversationHistory.scrollHeight;

    // Attach collapse button event listener
    const collapseBtn = responseLi.querySelector('.collapse-btn');
    const messageContent = responseLi.querySelector('.message-content');
    collapseBtn.addEventListener('click', function() {
        messageContent.classList.toggle('collapsed');
        this.textContent = messageContent.classList.contains('collapsed') ? 'Expand' : 'Collapse';
    });

    isTyping = true;

    try {
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => null);
            throw new Error(errorData?.message || "Failed to generate response");
        }

        const data = await response.json();
        let generatedResponse = data.response;

        generatedResponse = generatedResponse.replace(/\+/g, '');
        const sanitizedResponse = sanitizeHTML(generatedResponse);

        let formattedResponse = '';
        for (let i = 0; i < sanitizedResponse.length; i++) {
            formattedResponse += sanitizedResponse[i];
            messageContent.innerHTML = formatResponseText(formattedResponse);
            await new Promise(resolve => setTimeout(resolve, 10));
        }

        if (currentConversationId) {
            const conversation = conversations.find(conv => conv.id === currentConversationId);
            conversation.messages.push({ speaker: "LLaMA", content: sanitizedResponse });
        }

        isTyping = false;
    } catch (error) {
        messageContent.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
        console.error("Error:", error);
        isTyping = false;
    }
});

function addToConversationHistory(speaker, content) {
    const li = document.createElement("li");
    li.classList.add("fade-in");
    li.innerHTML = `
        <div class="message-header">
            <strong>${speaker}:</strong>
            <button class="collapse-btn">Collapse</button>
        </div>
        <div class="message-content">${formatResponseText(sanitizeHTML(content))}</div>
    `;
    const collapseBtn = li.querySelector('.collapse-btn');
    const messageContent = li.querySelector('.message-content');
    collapseBtn.addEventListener('click', function() {
        messageContent.classList.toggle('collapsed');
        this.textContent = messageContent.classList.contains('collapsed') ? 'Expand' : 'Collapse';
    });
    conversationHistory.appendChild(li);
    li.classList.add("show");
    conversationHistory.scrollTop = conversationHistory.scrollHeight;

    if (currentConversationId) {
        const conversation = conversations.find(conv => conv.id === currentConversationId);
        conversation.messages.push({ speaker, content });
    }
}

function sanitizeHTML(str) {
    var temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

function formatResponseText(text) {
    return marked.parse(text);
}

// Start with a new conversation
startNewConversation();
