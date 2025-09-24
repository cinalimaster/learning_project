const chatBox = document.getElementById('chatBox');
const userInput = document.getElementById('userInput');
const chatContainer = document.getElementById('chatContainer');
const chatButton = document.getElementById('chatButton');
const closeChat = document.getElementById('closeChat');
let sessionId = null;
let hasGreeted = sessionStorage.getItem('hasGreeted') === 'true';

// Validate DOM elements
if (!chatBox) {
    console.error('Error: chatBox element not found. Check HTML ID.');
}
if (!userInput) {
    console.error('Error: userInput element not found. Check HTML ID.');
}
if (!chatContainer || !chatButton || !closeChat) {
    console.error('Error: Chat widget elements not found.');
}

// Function to open chat with animation
function openChat() {
    chatContainer.style.display = 'flex';
    chatContainer.classList.add('chat-open');
    chatButton.style.display = 'none';
    chatBox.scrollTop = chatBox.scrollHeight; // Scroll to bottom

    // Show greeting message.
    if (!hasGreeted) {
    appendMessage(
      "Merhaba ✋😏 Bana belediye hizmetleri hakkında soru sorabilirsiniz. Örnek: Temizlik hizmetleri hakkında bilgi almak istiyorum temizlik işleri için belediye bana nasıl yardım edebilir?",
      false
    );
    hasGreeted = true;
    sessionStorage.setItem('hasGreeted', 'true');
  }
}



// Function to close chat with animation
function closeChatWidget() {
    chatContainer.classList.remove('chat-open');
    chatContainer.classList.add('chat-close');
    setTimeout(() => {
        chatContainer.style.display = 'none';
        chatContainer.classList.remove('chat-close');
        chatButton.style.display = 'flex';
    }, 300); // Match animation duration
}

// Event listeners for open/close
if (chatButton) {
    chatButton.addEventListener('click', openChat);
}
if (closeChat) {
    closeChat.addEventListener('click', closeChatWidget);
}

// Function to append messages to the chat box (updated for safe URL linking)
function appendMessage(message, isUser) {
    if (!chatBox) {
        console.error('Cannot append message: chatBox is not defined.');
        return;
    }

    console.log(`Appending message (isUser: ${isUser}):`, message);

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

    if (isUser) {
        // User messages are plain text
        messageDiv.textContent = message;
    } else {
        // Log raw bot message for debugging
        console.log('Raw bot message:', message);

        // Remove <think>... </think> tags and their content
        let processedMessage = message.replace(/<think>[\s\S]*?<\/think>/g, '').trim();

        // Log after removing <think> tags
        console.log('After removing <think>:', processedMessage);

        // Fallback if empty
        if (!processedMessage) {
            processedMessage = 'Bot yanıtı boş veya yalnızca düşünme içeriği içeriyor.';
            console.warn('Processed message is empty after removing <think> tags.');
        }

        // Only linkify URLs that are NOT already inside a tag (e.g., not in href="...").
        // This regex finds http(s):// URLs that are NOT preceded by href= or inside tags
        // Add target="_blank" to existing <a> tags that have an href but lack target="_blank".
        processedMessage = processedMessage
        // First, linkify plain URLs not inside href or tags
        .replace(
            /(?<!href=")(https?:\/\/[^\s"<>]+)/g,
            (url) => {
                // Strip trailing punctuation from the URL for the href and display text
                let cleanUrl = url;
                let trailing = '';
                const punct = ',.;:!?)';
                while (punct.includes(cleanUrl.slice(-1))) {
                    trailing = cleanUrl.slice(-1) + trailing;
                    cleanUrl = cleanUrl.slice(0, -1);
                }
                return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer">${cleanUrl}</a>${trailing}`;
            }
        )
        // Then, add target="_blank" to <a> tags that lack it
        .replace(
            /<a\s+href="([^"]+)"(?![^>]*target="_blank")([^>]*)>([^<]+)<\/a>/g,
            (match, url, attributes, text) => {
                // If rel attribute is not present, add it along with target
                const relAttribute = attributes.includes('rel=')
                    ? attributes
                    : `${attributes} rel="noopener noreferrer"`.trim();
                return `<a href="${url}" target="_blank" ${relAttribute}>${text}</a>`;
            }
        );

        // Set the HTML content safely
        messageDiv.innerHTML = processedMessage;
    }

    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Function to show or hide the "Düşünüyor..." indicator with animation (unchanged)
function setLoadingIndicator(isLoading) {
    if (!chatBox) {
        console.error('Cannot set loading indicator: chatBox is not defined.');
        return;
    }

    const thinkingIndicator = document.getElementById('thinkingIndicator');
    if (isLoading) {
        if (!thinkingIndicator) {
            const indicatorDiv = document.createElement('div');
            indicatorDiv.id = 'thinkingIndicator';
            indicatorDiv.className = 'bot-message thinking-animation';
            // Text is handled by CSS ::before pseudo-element
            chatBox.appendChild(indicatorDiv);
            console.log('Added animated Düşünüyor... indicator');
            // Scroll to bottom immediately
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    } else {
        if (thinkingIndicator) {
            thinkingIndicator.remove();
            console.log('Removed Düşünüyor... indicator');
        }
    }
}

// Function to handle sending a message (unchanged)
async function sendMessage() {
    if (!userInput) {
        console.error('Cannot send message: userInput is not defined.');
        return;
    }

    const message = userInput.value.trim();
    if (!message) {
        console.log('Empty message, ignoring.');
        return;
    }

    // Append the user's message
    appendMessage(message, true);
    userInput.value = '';

    // Show the "Düşünüyor..." indicator
    setLoadingIndicator(true);

    try {
        console.log('Sending request to /api/ask/ with message:', message, 'sessionId:', sessionId);
        const response = await fetch('/api/ask/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: message,
                session_id: sessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Received response:', data);

        if (data.session_id) {
            sessionId = data.session_id;
            console.log('Updated sessionId:', sessionId);
        }

        if (!data.answer) {
            throw new Error('No answer provided in response.');
        }

        // Append the bot's response
        appendMessage(data.answer, false);
    } catch (error) {
        console.error('Error during fetch:', error);
        appendMessage('Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin.', false);
    } finally {
        // Hide the "Düşünüyor..." indicator
        setLoadingIndicator(false);
    }
}

// Listen for the Enter key press to send a message (unchanged)
if (userInput) {
    userInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
} else {
    console.error('Cannot add keypress listener: userInput is not defined.');
}