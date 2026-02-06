let jwtToken = ""; // Initialize the token variable

document.addEventListener("DOMContentLoaded", function () {
    // Get DOM elements
    const chatArea = document.querySelector('.chat-area');
    const promptInput = document.querySelector('.prompt-input');
    const sendButton = document.querySelector('.send-button');
    const downloadBtn = document.querySelector('.download-button');
    const newChatButtonElement = document.querySelector('.new-chat-button'); // Get the new chat button
    const userInputElement = document.querySelector('.prompt-input'); // Get the input element

    // Display the initial bot message
    if (chatArea) {
        displayMessage('Hello! How can I assist you today?', 'bot');
    }
    // Define the function for handling new chat
    function startNewChat() {
        // Clear the chat area
        if (chatArea) {
            chatArea.innerHTML = '';
            
            // Optionally, add an initial bot message again
            displayMessage('Hello! How can I assist you today?', 'bot');
        }
        // Optionally, clear the chat history array
        chatHistory.length = 0;
        console.log('New chat started'); // For debugging
    }

    // Function to display a message
    function displayMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${sender}-message`);

        if (sender === 'bot') {
            const logoImg = document.createElement('img');
            logoImg.src = "https://systems-plus.com/wp-content/themes/systemsplus/favicon.png";
            logoImg.classList.add('bot-logo');
            messageDiv.appendChild(logoImg);
        }
        
         // Check if the text contains lines that look like bullet points
        const lines = text.split('\n');
        const fragment = document.createDocumentFragment();
        let inList = false;
        let ul;
        let lastElementWasList = false;

        lines.forEach((line, index) => {
            const trimmedLine = line.trim();
            const listItemMatch = trimmedLine.match(/^(\d+\.\s+)(.*)/);
            const relatableDocMatch = trimmedLine.match(/Most relatable document:\s+\*\*([^*]+)\*\*/i);
            
            if (relatableDocMatch) {
                const p = document.createElement('p');
                p.innerHTML = '<strong>Most relatable document:</strong> <a href="'+`${relatableDocMatch[1].trim()}`+'" target="_blank">'+`${relatableDocMatch[1].trim()}`+'</a>';
                fragment.appendChild(p);
                lastElementWasList = false;
                inList = false;
                if (ul) {
                    ul = null;
                }
            } else if (listItemMatch) {
                if (!inList) {
                    ul = document.createElement('ul');
                    fragment.appendChild(ul);
                    inList = true;
                    lastElementWasList = true;
                }
                const li = document.createElement('li');
                li.textContent = listItemMatch[2].trim();
                ul.appendChild(li);
            } else if (trimmedLine) {
                if (inList) {
                    inList = false;
                }
                const p = document.createElement('p');
                p.textContent = trimmedLine;
                fragment.appendChild(p);
                lastElementWasList = false;
            } else if (inList) {
                // If the line is empty and we are in a list, continue the list
            } else if (!lastElementWasList) {
                const br = document.createElement('br');
                fragment.appendChild(br);
            }
        });

        messageDiv.appendChild(fragment);
        chatArea.appendChild(messageDiv);
        chatArea.scrollTop = chatArea.scrollHeight;

        if (sender === 'bot') {
            const feedbackContainer = addFeedbackButtons(messageDiv, sender);
            if (feedbackContainer) {
                    addCopyButton(feedbackContainer, text); // Add copy button to the feedback container
                } else {
                    addCopyButton(messageDiv, text); // Fallback if no feedback container
                }
            } else {
                addFeedbackButtons(messageDiv, sender);
            }
        
       
        return messageDiv;   
    }

    function addCopyButton(containerElement, textToCopy) {
        const copyButton = document.createElement('button');
        copyButton.classList.add('copy-button');
        copyButton.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
        copyButton.addEventListener('click', () => {
            navigator.clipboard.writeText(textToCopy).then(() => {
                // Provide visual feedback
                const copiedMessage = document.createElement('div');
                copiedMessage.classList.add('copied-message');
                copiedMessage.textContent = 'Copied to clipboard!';
                containerElement.parentNode.insertBefore(copiedMessage, containerElement.nextSibling); // Insert below the message

                // Remove the message after a short delay
                setTimeout(() => {
                    copiedMessage.remove();
                }, 1500);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                const errorMessage = document.createElement('div');
                errorMessage.classList.add('copy-error-message');
                errorMessage.textContent = 'Failed to copy!';
                containerElement.parentNode.insertBefore(errorMessage, containerElement.nextSibling);
                setTimeout(() => {
                    errorMessage.remove();
                }, 1500);
            });
        });
        containerElement.appendChild(copyButton);
    }

    function addFeedbackButtons(messageDiv, sender) {
        if (sender === 'bot') {
            const feedbackContainer = document.createElement('div');
            feedbackContainer.classList.add('feedback-container');
            feedbackContainer.innerHTML = `
                <button class="feedback-button thumbs-up" onclick="window.sendFeedback('up', this)">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v10h12l2-7v-1a2 2 0 0 0-2-2h-5z"></path>
                    </svg>
                </button>
                <button class="feedback-button thumbs-down" onclick="window.sendFeedback('down', this)">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10 15v4a3 3 0 0 0 3 3l4-9V3H5l-2 7v1a2 2 0 0 0 2 2h5z"></path>
                    </svg>
                </button>
            `;
            messageDiv.appendChild(feedbackContainer);
            return feedbackContainer; // Return the container
        }
        return null;
    }

    let initialBotMessageShown = true; // Flag to track if the initial bot message is shown
    // Define sendMessage function
    async function sendMessage() {
        const question = userInputElement.value.trim();

        if (!question) {
            console.warn("No question entered!");
            return;
        }

        // Remove initial bot message on the first user interaction
        if (initialBotMessageShown) {
            const chatArea = document.querySelector('.chat-area');
            const firstBotMessage = chatArea.querySelector('.bot-message'); // Assuming the initial message has this class
            if (firstBotMessage) {
                firstBotMessage.remove();
            }
            initialBotMessageShown = false;
        }

        console.log("User question in sendMessage:", question);

        // Add user message to chat UI
        displayMessage(question, "user");
        userInputElement.value = ""; // Clear input field after sending message

        // Disable input field while waiting for response
        userInputElement.disabled = true;

        // Display "Bot is thinking..." message
        displayMessage("Bot is thinking...", "bot-thinking");


        try {
            if (!jwtToken) {
                alert("You are not logged in. Please log in first.");
                // Remove "Bot is thinking..." message
                const thinkingMessageElement = chatArea.querySelector('.bot-thinking-message');
                if (thinkingMessageElement) {
                    thinkingMessageElement.remove();
                }
                userInputElement.disabled = false;
                return;
            }
            const response = await fetch("http://www.nbpoc.com:5000/query", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${jwtToken}`
                    // "X-API-KEY": API_KEY // Include the API key in the headers if needed
                },
                body: JSON.stringify({ question: question })
            });

           // Remove "Bot is thinking..." message
           const thinkingMessageElement = chatArea.querySelector('.bot-thinking-message');
           if (thinkingMessageElement) {
               thinkingMessageElement.remove();
           }

            if (!response.ok) {
                const errorText = await response.text();
                console.error("Server Error:", errorText);
               // displayMessage(`Server Error: ${errorText}`, 'bot'); // Display error to user
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            if (data.answer) {
                let botMessage = data.answer;
                if (data.document_path) {
                    botMessage += `<br><a href="${data.document_path}" target="_blank">View Document</a>`;
                }
                displayMessage(botMessage, "bot");
                saveChatMessage(question, botMessage); // Update chat history for download
            } else {
                displayMessage("No response from the bot.", "bot");
            }
        } catch (error) {
            console.error("Fetch Error:", error);
            displayMessage("Error connecting to the server.", "bot");
            // Remove "Bot is thinking..." message
            const thinkingMessageElement = chatArea.querySelector('.bot-thinking-message');
            if (thinkingMessageElement) {
                thinkingMessageElement.remove();
            }
           
        } finally {
            userInputElement.disabled = false; // Re-enable input field after response or error
        }

        
    }
    window.sendMessage = sendMessage; // Make it globally accessible for event listeners


   /* window.sendMessage = async function () { // Make it a global function
        const messageText = promptInput.value.trim();
        if (!messageText) return;

        if (!jwtToken) {
            alert("You are not logged in. Please log in first.");
            return;
        }

        displayMessage(messageText, 'user');
        promptInput.value = '';

        // Simulate typing indicator (optional)
        const typingDiv = document.createElement('div');
        typingDiv.classList.add('message', 'bot-typing');
        typingDiv.textContent = 'Bot is thinking...';
        chatArea.appendChild(typingDiv);
        chatArea.scrollTop = chatArea.scrollHeight;

        try {
            const response = await fetch('http://www.nbpoc.com:5000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${jwtToken}` // If you have JWT authentication
                },
                body: JSON.stringify({ query: messageText }) // Assuming your API expects 'query'
            });

            chatArea.removeChild(typingDiv); // Remove typing indicator

            if (!response.ok) {
                const errorData = await response.json();
                displayMessage(`Error: ${errorData.error || 'Something went wrong'}`, 'bot');
                return;
            }

            const data = await response.json();
            displayMessage(data.response, 'bot'); // Assuming your API returns 'response'
            saveChatMessage(messageText, data.response); // Save to local storage for download
        } catch (error) {
            console.error('Error sending query:', error);
            chatArea.removeChild(typingDiv);
            displayMessage('Error: Could not communicate with the server.', 'bot');
        }
    };*/

    window.sendFeedback = function (type, element) { // Make it a global function
        const messageDiv = element.parentNode.parentNode; // Get the message container
        const botMessage = messageDiv.querySelector('.bot-message') ? messageDiv.querySelector('.bot-message').textContent : '';

        fetch('/api/feedback', { // Replace '/api/feedback' with your actual API endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwtToken}` // If you have JWT authentication
            },
            body: JSON.stringify({ message: botMessage, feedback_type: type })
        })
        .then(response => {
            if (!response.ok) {
                console.error('Feedback submission failed:', response.status);
                // Optionally provide user feedback
            } else {
                console.log('Feedback submitted:', type);
                // Optionally provide visual feedback on the button
            }
        })
        .catch(error => {
            console.error('Error submitting feedback:', error);
            // Optionally provide user feedback
        });
    };

    // Local storage for chat history (for download)
    const chatHistory = [];
    function saveChatMessage(userMessage, botMessage) {
        chatHistory.push({ user: userMessage, bot: botMessage });
    }

    window.downloadChatHistory = function () { // Make it a global function
        if (chatHistory.length === 0) {
            alert('No chat history to download.');
            return;
        }

        const filename = 'chat_history.txt';
        let text = '';
        chatHistory.forEach(entry => {
            text += `User: ${entry.user}\nBot: ${entry.bot}\n\n`;
        });

        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    };

    async function fetchToken() {
        try {
            const response = await fetch('http://www.nbpoc.com:5000/get_token', {
                method: 'GET' // Assuming your token endpoint uses GET
            });
            if (response.ok) {
                const data = await response.json();
                jwtToken = data.token;
                console.log('JWT Token:', jwtToken);
            } else {
                console.error('Failed to fetch token');
            }
        } catch (error) {
            console.error('Error fetching token:', error);
        }
    }

    
    // Event listeners
    if (sendButton) {
        sendButton.addEventListener('click', sendMessage);
    } else {
        console.error("Send button element not found!");
    }

    promptInput.addEventListener('keypress', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });

    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadChatHistory);
    } else {
        console.error("Download button element not found!");
    }

    // Add event listener for the new chat button
    if (newChatButtonElement) {
        newChatButtonElement.addEventListener('click', startNewChat);
    } else {
        console.error("New chat button element not found!");
    }

    fetchToken(); // Call fetchToken on page load
});