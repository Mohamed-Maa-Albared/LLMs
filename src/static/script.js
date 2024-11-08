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

        console.log(payload)

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
const screenshotBtn = document.getElementById('screenshot-btn');

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

    const formattedContent = formatResponseText(content);

    li.innerHTML = `
        <div class="message-header">
            <strong>${speaker}:</strong>
            <button class="collapse-btn">Collapse</button>
        </div>
        <div class="message-content">${formattedContent}</div>
    `;

    // Add response time if provided
    if (responseTime !== undefined) {
        const timeMessage = document.createElement("small");
        timeMessage.classList.add("response-time");
        timeMessage.textContent = `${responseTime}s`;
        li.appendChild(timeMessage);
    }

    // Add copy buttons to code blocks
    const codeBlocks = li.querySelectorAll('pre code');
    codeBlocks.forEach(block => {
        const copyBtn = document.createElement('button');
        copyBtn.innerHTML = `
            <img src="/static/assets/copy.png" alt="Copy" class="copy-icon" />
        `;
        copyBtn.classList.add('copy-btn');
        copyBtn.title = 'Copy code';
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent).then(() => {
                copyBtn.classList.add('copied');
                setTimeout(() => copyBtn.classList.remove('copied'), 2000);
            });
        });
        block.parentNode.style.position = 'relative'; // Ensure parent is relative for absolute positioning
        block.parentNode.appendChild(copyBtn);
    });

    // Implement collapsing functionality
    const collapseBtn = li.querySelector('.collapse-btn');
    const messageContent = li.querySelector('.message-content');
    collapseBtn.addEventListener('click', function () {
        messageContent.classList.toggle('collapsed');
        this.textContent = messageContent.classList.contains('collapsed') ? 'Expand' : 'Collapse';
        const timeMessage = li.querySelector('.response-time');
        if (timeMessage) {
            timeMessage.style.display = messageContent.classList.contains('collapsed') ? 'none' : 'block';
        }
    });

    // Add the message to the conversation history
    conversationHistory.appendChild(li);
    li.classList.add("show");
    conversationHistory.scrollTop = conversationHistory.scrollHeight;

    // Save to storage if required
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
            .map(msg => `${msg.speaker}: ${msg.content}`).join('\n') + `\nUser: ${prompt}`;
    } else {
        promptToSend = `User: ${prompt}`;
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
modeToggle.addEventListener("change", function () {
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

confirmPopupBtn.addEventListener("click", function () {
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
    // Decode HTML entities
    text = text.replace(/&lt;/g, '<').replace(/&gt;/g, '>');

    // Replace <thinking>, <output>, and <reflection> tags with custom HTML
    text = text.replace(/<thinking>([\s\S]*?)<\/thinking>/g, '<div class="thinking"><h4>Thinking:</h4>$1</div>');
    text = text.replace(/<output>([\s\S]*?)<\/output>/g, '<div class="output"><h4>Output:</h4>$1</div>');
    text = text.replace(/<Reflection>([\s\S]*?)<\/Reflection>/g, '<div class="reflection"><h4>Reflection:</h4>$1</div>');

    // Use marked.js to parse Markdown, including code blocks
    return marked.parse(text, {
        highlight: function (code, lang) {
            const language = hljs.getLanguage(lang) ? lang : 'plaintext';
            return hljs.highlight(code, { language }).value;
        },
        langPrefix: 'hljs language-'
    });
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

function addMultiActionButton() {
    const container = document.createElement('div');
    container.className = 'multi-action-container';

    // Main button
    const button = document.createElement('button');
    button.id = 'multi-action-btn';
    button.innerHTML = `
        <svg viewBox="0 0 24 24">
            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
        </svg>
    `;

    // Dropdown menu
    const dropdown = document.createElement('div');
    dropdown.className = 'action-dropdown';
    dropdown.innerHTML = `
        <div class="action-option" data-action="file">
            <svg viewBox="0 0 24 24">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
            </svg>
            <span>Upload File</span>
        </div>
        <div class="action-option" data-action="image">
            <svg viewBox="0 0 24 24">
                <path d="M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2zM8.5 13.5l2.5 3 3.5-4.5 4.5 6H5l3.5-4.5z"/>
            </svg>
            <span>Upload Image</span>
        </div>
        <div class="action-option" data-action="screenshot">
            <svg viewBox="0 0 24 24">
                <path d="M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2zM8.5 13.5l2.5 3 3.5-4.5 4.5 6H5l3.5-4.5z"/>
            </svg>
            <span>Take Screenshot</span>
        </div>
        <div class="action-option" data-action="voice">
            <svg viewBox="0 0 24 24">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/>
            </svg>
            <span>Record Voice</span>
        </div>
    `;

    // Hidden file inputs
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.className = 'hidden-input';
    fileInput.id = 'file-input';

    const imageInput = document.createElement('input');
    imageInput.type = 'file';
    imageInput.accept = 'image/*';
    imageInput.className = 'hidden-input';
    imageInput.id = 'image-input';

    container.appendChild(button);
    container.appendChild(dropdown);
    container.appendChild(fileInput);
    container.appendChild(imageInput);

    return container;
}

// Configuration object for file handling
const CONFIG = {
    uploadEndpoints: {
        file: '/api/upload/files',
        image: '/api/upload/images',
        screenshot: '/api/upload/screenshots',
        voice: '/api/upload/voice'
    }
};

function initializeMultiActionButton() {
    console.log('Initializing multi-action button');

    const multiActionBtn = document.getElementById('multi-action-btn');
    const dropdown = document.querySelector('.action-dropdown');
    const fileInput = document.getElementById('file-input');
    const imageInput = document.getElementById('image-input');

    if (!multiActionBtn || !dropdown) {
        console.error('Required elements not found:', {
            multiActionBtn: !!multiActionBtn,
            dropdown: !!dropdown
        });
        return;
    }

    let mediaRecorder = null;
    let audioChunks = [];

    // Handle file uploads
    async function uploadFile(file, type) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(CONFIG.uploadEndpoints[type], {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Upload failed');
            }

            const result = await response.json();
            console.log(`${type} uploaded successfully:`, result);
            return result;
        } catch (error) {
            console.error(`${type} upload failed:`, error);
            throw error;
        }
    }

    // Toggle dropdown
    multiActionBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('Button clicked');
        dropdown.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.multi-action-container')) {
            dropdown.classList.remove('show');
        }
    });

    // Handle file input
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            try {
                const result = await uploadFile(file, 'file');
                console.log('File uploaded:', result);
            } catch (error) {
                alert('Failed to upload file: ' + error.message);
            }
        }
    });

    // Handle image input
    imageInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            try {
                const result = await uploadFile(file, 'image');
                console.log('Image uploaded:', result);
            } catch (error) {
                alert('Failed to upload image: ' + error.message);
            }
        }
    });

    // Handle dropdown options
    dropdown.addEventListener('click', async (e) => {
        const option = e.target.closest('.action-option');
        if (!option) return;

        const action = option.dataset.action;

        switch (action) {
            case 'file':
                fileInput.click();
                break;
            case 'image':
                imageInput.click();
                break;
            case 'screenshot':
                try {
                    const canvas = await html2canvas(document.body);
                    canvas.toBlob(async (blob) => {
                        try {
                            const file = new File([blob], 'screenshot.png', { type: 'image/png' });
                            const result = await uploadFile(file, 'screenshot');
                            console.log('Screenshot uploaded:', result);
                        } catch (error) {
                            alert('Failed to upload screenshot: ' + error.message);
                        }
                    });
                } catch (error) {
                    console.error('Screenshot failed:', error);
                    alert('Failed to take screenshot: ' + error.message);
                }
                break;
            case 'voice':
                if (!mediaRecorder) {
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                        mediaRecorder = new MediaRecorder(stream);

                        mediaRecorder.ondataavailable = (e) => {
                            audioChunks.push(e.data);
                        };

                        mediaRecorder.onstop = async () => {
                            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                            try {
                                const file = new File([audioBlob], 'recording.wav', { type: 'audio/wav' });
                                const result = await uploadFile(file, 'voice');
                                console.log('Voice recording uploaded:', result);
                            } catch (error) {
                                alert('Failed to upload voice recording: ' + error.message);
                            }
                            audioChunks = [];
                        };

                        mediaRecorder.start();
                        option.innerHTML += '<span class="recording-indicator">Recording...</span>';
                    } catch (error) {
                        console.error('Failed to start recording:', error);
                        alert('Failed to start recording: ' + error.message);
                    }
                } else {
                    mediaRecorder.stop();
                    mediaRecorder = null;
                    const indicator = option.querySelector('.recording-indicator');
                    if (indicator) indicator.remove();
                }
                break;
        }

        dropdown.classList.remove('show');
    });

    console.log('Multi-action button initialized');
}

// Initialize when the DOM is ready
document.addEventListener('DOMContentLoaded', initializeMultiActionButton);