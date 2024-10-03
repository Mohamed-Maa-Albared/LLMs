// Conversation class to encapsulate conversation-specific state and methods
class Conversation {
    constructor(id, name) {
        this.id = id;
        this.name = name;
        this.messages = [];
        this.isGenerating = false;
        this.abortController = null;
        this.currentResponse = '';
    }

    async generateResponse(prompt, model, temperature) {
        if (this.isGenerating) {
            console.log('Already generating a response for this conversation');
            return;
        }

        this.isGenerating = true;
        this.startTime = Date.now()
        this.abortController = new AbortController();

        const payload = {
            prompt: prompt,
            model: model,
            temperature: temperature
        };

        try {
            const response = await fetch("/api/generate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload),
                signal: this.abortController.signal
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.message || "Failed to generate response");
            }

            const data = await response.json();
            let generatedResponse = data.response.replace(/\+/g, '');
            const sanitizedResponse = sanitizeHTML(generatedResponse);

            this.currentResponse = sanitizedResponse;
            this.messages.push({
                speaker: "LLaMA",
                content: sanitizedResponse,
                responseTime: ((Date.now() - this.startTime) / 1000).toFixed(2)
            });

            updateConversationUI(this.id);
            saveConversationsToLocalStorage();
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error("Error:", error);
                this.currentResponse = `<span style="color: red;">Error: ${error.message}</span>`;
            }
        } finally {
            this.isGenerating = false;
            this.abortController = null;
            updateConversationUI(this.id);
        }
    }

    abort() {
        if (this.abortController) {
            this.abortController.abort();
        }
    }
}

// Global state
let conversations = new Map();
let currentConversationId = null;
let temperature = 0.7;

// DOM elements
const form = document.getElementById("prompt-form");
const conversationHistory = document.getElementById("conversation-history");
const conversationList = document.getElementById("conversation-list");
const newConversationBtn = document.getElementById("new-conversation-btn");
const darkModeToggle = document.getElementById("dark-mode-toggle");
const settingsShelf = document.getElementById("settings-shelf");
const settingsIcon = document.getElementById("settings-icon");
const modelSelect = document.getElementById("model-select");
const modeToggle = document.getElementById("mode-toggle");
const deletePopup = document.getElementById("delete-popup");
const cancelPopupBtn = document.getElementById("cancel-popup");
const confirmPopupBtn = document.getElementById("confirm-popup");
const promptInput = document.getElementById("prompt");

// Load conversations from localStorage
function loadConversationsFromLocalStorage() {
    const savedConversations = localStorage.getItem('conversations');
    if (savedConversations) {
        const conversationsArray = JSON.parse(savedConversations);
        conversations = new Map(conversationsArray.map(conv => [conv.id, new Conversation(conv.id, conv.name)]));
        conversationsArray.forEach(conv => {
            conversations.get(conv.id).messages = conv.messages;
        });
        updateConversationList();
    }
}

// Save conversations to localStorage
function saveConversationsToLocalStorage() {
    const conversationsArray = Array.from(conversations.values()).map(conv => ({
        id: conv.id,
        name: conv.name,
        messages: conv.messages
    }));
    localStorage.setItem('conversations', JSON.stringify(conversationsArray));
}

function startNewConversation() {
    const newConversation = new Conversation(Date.now(), `Conversation ${conversations.size + 1}`);
    conversations.set(newConversation.id, newConversation);
    currentConversationId = newConversation.id;
    updateConversationList();
    clearConversationHistory();
    saveConversationsToLocalStorage();
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
        
        const nameSpan = li.querySelector('.conversation-name');
        const deleteBtn = li.querySelector('.delete-btn');

        li.addEventListener('click', () => {
            loadConversation(conv.id);
        });

        nameSpan.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id, li);
        });

        nameSpan.addEventListener('blur', (e) => {
            e.stopPropagation();
            conv.name = e.target.textContent;
            saveConversationsToLocalStorage();
        });

        nameSpan.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                nameSpan.blur();
            }
        });

        if (conv.isGenerating) {
            li.classList.add('generating');
        }

        conversationList.appendChild(li);
    });
}

function loadConversation(id) {
    currentConversationId = id;
    clearConversationHistory();
    const conversation = conversations.get(id);
    if (conversation) {
        conversation.messages.forEach(msg => addToConversationHistory(msg.speaker, msg.content, msg.responseTime, false));
        if (conversation.isGenerating) {
            addGeneratingMessage();
        }
    } else {
        console.error(`Conversation with id ${id} not found`);
        startNewConversation();
    }
}

function clearConversationHistory() {
    conversationHistory.innerHTML = '';
}

function addToConversationHistory(speaker, content, responseTime, saveToStorage = true) {
    const li = document.createElement("li");
    li.classList.add("fade-in");
    
    li.innerHTML = `
        <div class="message-header">
            <strong>${speaker}:</strong>
            <button class="collapse-btn">Collapse</button>
        </div>
        <div class="message-content">${formatResponseText(content)}</div>
    `;

    if (responseTime != undefined) {
        const timeMessage = document.createElement("small");
        timeMessage.classList.add("response-time");
        timeMessage.textContent = `${responseTime}s`;
        li.appendChild(timeMessage);
    }

    const collapseBtn = li.querySelector('.collapse-btn');
    const messageContent = li.querySelector('.message-content');
    collapseBtn.addEventListener('click', function() {
        messageContent.classList.toggle('collapsed');
        this.textContent = messageContent.classList.contains('collapsed') ? 'Expand' : 'Collapse';
        const timeMessage = li.querySelector('.response-time');
        if (timeMessage) {
            timeMessage.style.display = messageContent.classList.contains('collapsed') ? 'none' : 'block';
        }
    });

    conversationHistory.appendChild(li);
    li.classList.add("show");
    conversationHistory.scrollTop = conversationHistory.scrollHeight;

    if (currentConversationId && saveToStorage) {
        const conversation = conversations.get(currentConversationId);
        if (conversation) {
            conversation.messages.push({
                speaker, 
                content, 
                responseTime: responseTime || undefined
            });
            saveConversationsToLocalStorage();
        } else {
            console.error(`Conversation with id ${currentConversationId} not found`);
            startNewConversation();
        }
    }
}

function addGeneratingMessage() {
    const li = document.createElement("li");
    li.innerHTML = `
        <div class="message-header">
            <strong>LLaMA:</strong>
        </div>
        <div class="message-content"><span class="typing">LLaMA is thinking</span></div>
    `;
    conversationHistory.appendChild(li);
    conversationHistory.scrollTop = conversationHistory.scrollHeight;
}

function updateConversationUI(conversationId) {
    if (conversationId === currentConversationId) {
        clearConversationHistory();
        const conversation = conversations.get(conversationId);
        conversation.messages.forEach(msg => addToConversationHistory(msg.speaker, msg.content, msg.responseTime, false));
        if (conversation.isGenerating) {
            addGeneratingMessage();
        }
    }
    updateConversationList();
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const prompt = promptInput.value.trim();
    const selectedModel = modelSelect.value;
    promptInput.value = "";

    if (prompt === "") return;

    if (!currentConversationId) {
        startNewConversation();
    }

    const conversation = conversations.get(currentConversationId);
    addToConversationHistory("You", prompt);

    const includeHistory = document.getElementById("include-history").checked;
    let promptToSend;
    if (includeHistory) {
        promptToSend = conversation.messages
            .filter(msg => msg.speaker !== "Response Time")
            .map(msg => `${msg.speaker}: ${msg.content}`).join('\n') + `\nYou: ${prompt}`;
    } else {
        promptToSend = `You: ${prompt}`;
    }

    conversation.generateResponse(promptToSend, selectedModel, temperature);
    updateConversationUI(currentConversationId);
});

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
    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('dark-mode', 'enabled');
        darkModeToggle.textContent = 'Light Mode';
    } else {
        localStorage.setItem('dark-mode', 'disabled');
        darkModeToggle.textContent = 'Dark Mode';
    }
});

// Listen for changes to the mode toggle
modeToggle.addEventListener("change", function() {
    temperature = this.checked ? 1 : 0.7;
    console.log("Temperature set to:", temperature);
});

settingsIcon.addEventListener("click", () => {
    settingsShelf.classList.toggle("open");
});

function deleteConversation(id, element) {
    openDeletePopup(id, element);
}

function openDeletePopup(id, element) {
    conversationToDelete = id;
    const rect = element.getBoundingClientRect();
    deletePopup.style.top = `${rect.top + window.scrollY}px`;
    deletePopup.style.left = `${rect.left + rect.width / 2 - 100}px`;
    deletePopup.style.display = "block";
    conversationList.classList.add('blur');
    setTimeout(() => deletePopup.classList.add("show"), 10);
}

function closeDeletePopup() {
    deletePopup.classList.remove("show");
    setTimeout(() => {
        deletePopup.style.display = "none";
        conversationList.classList.remove('blur');
    }, 300);
}

cancelPopupBtn.addEventListener("click", closeDeletePopup);

confirmPopupBtn.addEventListener("click", function() {
    if (conversationToDelete) {
        conversations.delete(conversationToDelete);
        if (currentConversationId === conversationToDelete) {
            currentConversationId = null;
            clearConversationHistory();
        }
        updateConversationList();
        saveConversationsToLocalStorage();
        closeDeletePopup();
    }
});

promptInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event("submit"));
    }
});

function sanitizeHTML(str) {
    var temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}

function formatResponseText(text) {
    return marked.parse(text);
}

// Initialize the application
document.addEventListener("DOMContentLoaded", function () {
    loadConversationsFromLocalStorage();

    if (conversations.size === 0) {
        startNewConversation();
    } else {
        const lastConversationId = Array.from(conversations.keys()).pop();
        loadConversation(lastConversationId);
    }

    fetch("/api/models")
        .then(response => {
            if (!response.ok) {
                throw new Error("Failed to fetch models");
            }
            return response.json();
        })
        .then(models => {
            if (models.length === 0) {
                console.error("No models available");
                return;
            }

            models.forEach(model => {
                const option = document.createElement("option");
                option.value = model.name;
                option.textContent = model.name;
                modelSelect.appendChild(option);
            });
        })
        .catch(error => console.error("Error fetching models:", error));
});