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

let isTyping = false;
let conversations = [];
let currentConversationId = null;
let temperature = 0.7; 
let abortController = null;
let conversationToDelete = null;

// Load conversations from localStorage
function loadConversationsFromLocalStorage() {
    const savedConversations = localStorage.getItem('conversations');
    if (savedConversations) {
        conversations = JSON.parse(savedConversations);
        updateConversationList();
    }
}

// Save conversations to localStorage
function saveConversationsToLocalStorage() {
    localStorage.setItem('conversations', JSON.stringify(conversations));
}

newConversationBtn.addEventListener("click", startNewConversation);

document.addEventListener("DOMContentLoaded", function () {
    loadConversationsFromLocalStorage(); // Load conversations when the page loads

    if (conversations.length === 0) {
        startNewConversation();
    } else {
        // Load the most recent conversation
        const mostRecentConversation = conversations[conversations.length - 1];
        if (mostRecentConversation) {
            loadConversation(mostRecentConversation.id);
        } else {
            startNewConversation();
        }
    }

    const modelSelect = document.getElementById("model-select");

    if (!modelSelect) {
        console.error("Model select element not found");
        return;
    }

    // Fetch models from the API
    fetch("/api/models")
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                throw new Error("Failed to fetch models");
            }
            return response.json();
        })
        .then(models => {
            console.log("Models fetched:", models);

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

// Listen for changes to the mode toggle
modeToggle.addEventListener("change", function() {
    if (this.checked) {
        temperature = 1;  // Set to Creative temperature
        console.log("Temperature set to Creative:", temperature);
    } else {
        temperature = 0.7;  // Set to Precise temperature
        console.log("Temperature set to Precise:", temperature);
    }
});

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
        
        const nameSpan = li.querySelector('.conversation-name');
        const deleteBtn = li.querySelector('.delete-btn');

        // Add click event to load the conversation when the list item is clicked
        li.addEventListener('click', () => {
            loadConversation(conv.id);
        });

        // Prevent the conversation from loading when clicking on editable name or delete button
        nameSpan.addEventListener('click', (e) => {
            e.stopPropagation();
        });
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            deleteConversation(conv.id, li);
        });

        // Update the conversation name when editing finishes (blur)
        nameSpan.addEventListener('blur', (e) => {
            e.stopPropagation();
            conv.name = e.target.textContent;
            saveConversationsToLocalStorage();  // Save name changes
        });

        // Save the name and exit editing mode on 'Enter' key press
        nameSpan.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                nameSpan.blur();  // Exit the contenteditable mode
            }
        });

        // Add the list item to the conversation list
        conversationList.appendChild(li);
    });
}

function deleteConversation(id, element) {
    openDeletePopup(id, element);  // Open the custom delete pop-up near the conversation element
}


function loadConversation(id) {
    currentConversationId = id;
    clearConversationHistory();
    const conversation = conversations.find(conv => conv.id === id);
    conversation.messages.forEach(msg => addToConversationHistory(msg.speaker, msg.content, msg.responseTime));
}

function clearConversationHistory() {
    conversationHistory.innerHTML = '';
}

form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (isTyping) return;

    const promptInput = document.getElementById("prompt");
    const prompt = promptInput.value.trim();
    const selectedModel = modelSelect.value;
    promptInput.value = "";

    if (prompt === "") return;

    if (!currentConversationId) {
        startNewConversation();
    }

    addToConversationHistory("You", prompt);

    // Get the toggle value
    const includeHistory = document.getElementById("include-history").checked;

    // Prepare the prompt to send (excluding response time)
    let promptToSend;
    if (includeHistory && currentConversationId) {
        const conversation = conversations.find(conv => conv.id === currentConversationId);
        promptToSend = conversation.messages
            .filter(msg => msg.speaker !== "Response Time")  // Exclude time message
            .map(msg => `${msg.speaker}: ${msg.content}`).join('\n');  // Only content gets included
    } else {
        promptToSend = `You: ${prompt}`;
    }

    // Create the payload, including the selected model
    const payload = {
        prompt: promptToSend,
        model: selectedModel,
        temperature: temperature
    };

    console.log("payload:", payload);

    const responseLi = document.createElement("li");
    responseLi.style.position = "relative"; // Ensure relative positioning for the time message
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

    // Create a new AbortController
    abortController = new AbortController();

    // Start timer to calculate the response time
    const startTime = performance.now();

    try {
        const response = await fetch("/api/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload),
            signal: abortController.signal
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
            await new Promise(resolve => requestAnimationFrame(resolve));
            
            // Check if the request has been aborted
            if (abortController.signal.aborted) {
                throw new DOMException('Aborted', 'AbortError');
            }
        }

        // Stop the timer after the response is fully generated
        const endTime = performance.now();
        const duration = (endTime - startTime) / 1000;  // Convert milliseconds to seconds

        // Append the time message to the response
        const timeMessage = document.createElement("small");
        timeMessage.classList.add("response-time");  // Add class for styling
        timeMessage.textContent = `${duration.toFixed(2)}s`;
        responseLi.appendChild(timeMessage);

        // Save the response to the conversation history, including the time
        if (currentConversationId) {
            const conversation = conversations.find(conv => conv.id === currentConversationId);
            conversation.messages.push({
                speaker: "LLaMA",
                content: sanitizedResponse,
                responseTime: duration.toFixed(2)  // Store the time
            });
            saveConversationsToLocalStorage();
        }

    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Fetch aborted');
        } else {
            messageContent.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
            console.error("Error:", error);
        }
    } finally {
        isTyping = false;
        abortController = null;
    }
});

function addToConversationHistory(speaker, content, responseTime, saveToStorage = true) {
    const li = document.createElement("li");
    li.classList.add("fade-in");
    
    // Main message content
    li.innerHTML = `
        <div class="message-header">
            <strong>${speaker}:</strong>
            <button class="collapse-btn">Collapse</button>
        </div>
        <div class="message-content">${formatResponseText(sanitizeHTML(content))}</div>
    `;

    // Conditionally add the response time if it exists
    if (responseTime != undefined) {
        const timeMessage = document.createElement("small");
        timeMessage.classList.add("response-time");
        timeMessage.textContent = `${responseTime}s`;
        li.appendChild(timeMessage);  // Append the time only if it exists
    }

    // Add the collapse functionality
    const collapseBtn = li.querySelector('.collapse-btn');
    const messageContent = li.querySelector('.message-content');
    collapseBtn.addEventListener('click', function() {
        messageContent.classList.toggle('collapsed');
        
        // Toggle the collapse button text
        this.textContent = messageContent.classList.contains('collapsed') ? 'Expand' : 'Collapse';
        
        // Toggle the visibility of the response time
        const timeMessage = li.querySelector('.response-time'); // Get the response time element
        if (timeMessage) {
            timeMessage.style.display = messageContent.classList.contains('collapsed') ? 'none' : 'block';
        }
    });

    // Add the message to the conversation history and scroll to the bottom
    conversationHistory.appendChild(li);
    li.classList.add("show");
    conversationHistory.scrollTop = conversationHistory.scrollHeight;

    // Save the conversation to local storage if necessary
    if (currentConversationId && saveToStorage) {
        const conversation = conversations.find(conv => conv.id === currentConversationId);
        if (conversation) {
            // Save the message with or without response time
            conversation.messages.push({
                speaker, 
                content, 
                responseTime: responseTime || undefined // Save time if it exists, else undefined
            });
            saveConversationsToLocalStorage();
        } else {
            console.error(`Conversation with id ${currentConversationId} not found`);
            startNewConversation();
        }
    }
}
function loadConversation(id) {
    currentConversationId = id;
    clearConversationHistory();
    const conversation = conversations.find(conv => conv.id === id);
    if (conversation) {
        conversation.messages.forEach(msg => addToConversationHistory(msg.speaker, msg.content, msg.responseTime, false));
    } else {
        console.error(`Conversation with id ${id} not found`);
        startNewConversation();
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

settingsIcon.addEventListener("click", () => {
    settingsShelf.classList.toggle("open");
});

function openDeletePopup(id, element) {
    conversationToDelete = id;

    // Position the pop-up near the clicked conversation
    const rect = element.getBoundingClientRect();
    deletePopup.style.top = `${rect.top + window.scrollY}px`;
    deletePopup.style.left = `${rect.left + rect.width / 2 - 100}px`;  // Center the pop-up
    deletePopup.style.display = "block";

    // Add the blur class to the conversation list
    conversationList.classList.add('blur');

    // Add transition class to animate the pop-up
    setTimeout(() => deletePopup.classList.add("show"), 10);
}

function closeDeletePopup() {
    deletePopup.classList.remove("show");
    setTimeout(() => {
        deletePopup.style.display = "none";  // Hide the pop-up after animation
        conversationList.classList.remove('blur');  // Remove blur effect
    }, 300);
}

// Attach event listeners to buttons in the pop-up
cancelPopupBtn.addEventListener("click", closeDeletePopup);

confirmPopupBtn.addEventListener("click", function() {
    if (conversationToDelete) {
        // Perform deletion of the conversation
        conversations = conversations.filter(conv => conv.id !== conversationToDelete);
        if (currentConversationId === conversationToDelete) {
            currentConversationId = null;
            clearConversationHistory();
        }
        updateConversationList();
        saveConversationsToLocalStorage();  // Save after deletion

        closeDeletePopup();  // Close the pop-up after deletion
    }
});

// Listen for "Enter" key press on the prompt input
promptInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();  // Prevent the default behavior (new line)
        form.dispatchEvent(new Event("submit"));  // Trigger form submission
    }
});

// Start with a new conversation
startNewConversation();