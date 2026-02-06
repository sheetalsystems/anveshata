let jwtToken = ""; // Initialize the token variable


document.addEventListener("DOMContentLoaded", function () {
    // Create Chatbot Button
    const chatbotToggle = document.createElement("button");
    chatbotToggle.classList.add("chatbot-toggle");
    chatbotToggle.innerHTML = "&#128172;";  // Chatbot icon
    chatbotToggle.onclick = toggleChat;
    document.body.appendChild(chatbotToggle);

    // Create Chatbot Container
    const chatContainer = document.createElement("div");
    chatContainer.classList.add("chat-container");
    chatContainer.id = "chatContainer";
    chatContainer.innerHTML = `
           <div class="chat-header">
            SYSTEMS+ <br>
            <div class="chat-controls">
            <span  class="center-text" style="font-size: 12px; color: gray;">NBPOC</span>

<button id="toggle-btn" onclick="toggleChatSize()" aria-label="Toggle">
  <svg id="toggle-icon" width="24" height="24" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="10" stroke="gray" stroke-width="1" />
    <path id="toggle-path" d="M14 8l-4 4 4 4" fill="none" stroke="gray" stroke-width="2" stroke-linecap="round" >
  </svg>
</button>
            </div>
        </div>
        <div class="chat-box" id="chatBox"></div>
        <div class="chat-input">
            <form method="post">
                <input type="text" name="question" id="userInput" placeholder="Ask a question..." required>
    
<button type="submit" id="sendBtn" style="background-color:#2F3146; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer;">
  <i class="fas fa-location-arrow" style="color: white; font-size: 18px; "></i>
</button>

                
                  <button type="button" id="voiceButton">
					<i class="fa-solid fa-microphone"></i> <!-- Mic Icon -->
				  </button>
                   <button type="button" id="downloadBtn"   style="background-color:#2F3146; color: white;">
                <i class="fas fa-download" color="#2F3146"></i> <!-- Font Awesome download icon -->
                 </button>
            </form>
        </div>
    `;
    document.body.appendChild(chatContainer);

    const sendButton = document.querySelector(".chat-input button[type='submit']");
    sendButton.addEventListener("click", function(event) {
        event.preventDefault(); // Prevent form submission
        sendMessage();
    });


    const downloadBtn = document.getElementById("downloadBtn");
    downloadBtn.addEventListener("click", function(event) {
        event.preventDefault(); // Prevent form submission or other default actions
        downloadPdf();  // Trigger the downloadPdf method
    });

  

    // Load previous chat state
    checkState();
    loadChatHistory();
});


document.addEventListener("DOMContentLoaded", async function () {
    try {
        jwtToken = sessionStorage.getItem("jwtToken");

        if (!jwtToken) {
            console.log("No token found in sessionStorage. Fetching from backend...");
        // Fetch the token from the backend
        const response = await fetch("http://127.0.0.1:5000/get_token", {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error("Failed to fetch token. Please log in again.");
        }
        if (response.ok) {
        const data = await response.json();
        jwtToken = data.token; // Store the token in memory
        console.log("Token fetched successfully:", jwtToken);

        // Optionally store the token in sessionStorage for reuse
        sessionStorage.setItem("jwtToken", jwtToken);
    } else {
        console.log("Token found in sessionStorage:", jwtToken);
    }
        }
    // Use the token in your API calls
    console.log("JWT Token ready for use:", jwtToken);

} catch (error) {
    console.error("Error during token fetch:", error);
    alert("Failed to fetch token. Please log in manually.");
}
});

// Function to fetch the token from the login endpoint
// async function fetchToken(username, password) {
//     try {
//         const response = await fetch("http://127.0.0.1:5000/login", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify({ username, password }) // Send login credentials
//         });

//         if (!response.ok) {
//             throw new Error(`Failed to fetch token: ${response.statusText}`);
//         }

//         const data = await response.json();
//         jwtToken = data.token; // Assuming the API returns { "token": "your_jwt_token" }
//         console.log("Token fetched successfully:", jwtToken);

//         // Optionally, store the token in sessionStorage for reuse
//         sessionStorage.setItem("jwtToken", jwtToken);
//     } catch (error) {
//         console.error("Error fetching token:", error);
//         alert("Failed to fetch token. Please check your credentials.");
//     }
// }


// The function to download the PDF
function loadJsPDF(callback) {
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js";
    script.onload = callback;
    document.head.appendChild(script);
}


function downloadPdf() {
    // alert("Download PDF button clicked!"); // Debugging line
    // Wait for jsPDF to load
    loadJsPDF(() => {
        const { jsPDF } = window.jspdf;  // Access jsPDF from the global window object
        const chatHistory = JSON.parse(sessionStorage.getItem("chatHistory")) || [];
        console.log("Chat History in sessionStorage:", chatHistory);

        if (chatHistory.length === 0) {
            console.log("No chat history found. Please interact with the chatbot first.");
            return;
        }

        // Create a new jsPDF instance
        const doc = new jsPDF();

        // Title of the PDF
        doc.text("Chat-bot History", 20, 20);
          // Set some basic font settings
          doc.setFont("helvetica", "normal");
          doc.setFontSize(12);

        let yPosition = 30;  // Y position for text
        const maxWidth = 180; // Adjust based on your page's margins

        chatHistory.forEach((chat, index) => {
            let question = chat.question || "[No Question]";  // Default if question is missing
            let answer = chat.answer || "[No Answer]"; 

            answer = answer.replace(/<[^>]*>/g, '');  // Removes all HTML tags
            
            
            const linkRegex = /(http[s]?:\/\/[^\s]+)/g;
            let links = answer.match(linkRegex);

            // If there are any links, extract them
            if (links && links.length > 0) {
                // Append the link text to the answer
                answer = answer.replace(linkRegex, '');  // Remove the link from the answer text
                answer += "\nLinks: " + links.join('\n');  // Add links at the end of the answer
            }

             // Add the question and answer to the PDF
             doc.text(`Q${index + 1}: ${question}`, 20, yPosition);
             yPosition += 10;  // Move down after question

              // Add the answer to the PDF with text wrapping
            const answerLines = doc.splitTextToSize(`A${index + 1}: ${answer}`, maxWidth);
            
            doc.text(answerLines, 20, yPosition);
            yPosition += answerLines.length * 10 + 5;  // Adjust position based on number of lines in the answer

            if (yPosition + (answerLines.length)> 270) { // If the yPosition exceeds the bottom of the page
                doc.addPage();  // Add a new page
                yPosition = 20;  // Reset yPosition to the top of the new page
            }
 
         });


        // Trigger the download
        doc.save("chat_history.pdf");
    });
}
// function downloadPdf() {
//     fetch("http://127.0.0.1:5000/download_pdf", {
//         method: "GET"
//         // headers: {
//         //     "X-API-KEY": API_KEY // Include the API key in the headers
//         // }
//     })
//     .then(response => {
//         if (!response.ok) {
//             throw new Error('Network response was not ok.');
//         }
//         return response.blob(); // Convert the response into a blob (PDF file)
//     })
//     .then(blob => {
//         // Create a link element to trigger the download
//         const url = window.URL.createObjectURL(blob);
//         const a = document.createElement("a");
//         a.href = url;
//         a.download = "chat_history.pdf";  // Set the desired filename for the download
//         document.body.appendChild(a);
//         a.click();  // Trigger the download
//         a.remove();  // Remove the link after triggering download
//     })
//     .catch(error => {
//         console.error("Error downloading PDF:", error);
//     });
// }

function minimizeChat() {
    const chatContainer = document.getElementById("chatContainer");
    const chatbotToggle = document.querySelector(".chatbot-toggle");

    // Minimize the chat window (shrink and move to toggle state)
    chatContainer.classList.remove("active");
    sessionStorage.setItem("chatState", "minimized");

    // Show the toggle button again after minimize
    chatbotToggle.style.display = "flex";  // Show chat toggle button when minimized
}


window.addEventListener("load", async function () {
    if (performance.getEntriesByType("navigation")[0].type === "reload") {
        console.log("Page refreshed! Clearing session and UI storage...");

        // Clear chat history from sessionStorage FIRST
        sessionStorage.removeItem("chatHistory");

        // Clear chat messages from the UI IMMEDIATELY
        const chatBox = document.getElementById("chatBox");
        if (chatBox) chatBox.innerHTML = "";

    }
});

function toggleChat() {
    
    const chatContainer = document.getElementById("chatContainer");
    const chatbotToggle = document.querySelector(".chatbot-toggle");
    const isOpening = !chatContainer.classList.contains("active");

    // Toggle chat window open/close
    chatContainer.classList.toggle("active");
     // If opening, apply fullscreen directly
     if (isOpening) {
        chatContainer.classList.add("fullscreen");
        chatContainer.classList.add("expanded");

        // Set toggle icon to minimize view
        const togglePath = document.getElementById("toggle-path");
        togglePath.setAttribute("d", "M10 8l4 4-4 4");
    } else {
        chatContainer.classList.remove("fullscreen");
        chatContainer.classList.remove("expanded");

        // Reset toggle icon to expand view
        const togglePath = document.getElementById("toggle-path");
        togglePath.setAttribute("d", "M14 8l-4 4 4 4");
    }
    // Store state
    sessionStorage.setItem("chatState", isOpening ? "expanded" : "contracted");
}

function checkState() {
    const chatContainer = document.getElementById("chatContainer");
    const saveState = sessionStorage.getItem("chatState");
    const chatbotToggle = document.querySelector(".chatbot-toggle");

    if (saveState === "expanded") {
        
        chatContainer.classList.add("active");
      } else if (saveState === "contracted") {
        chatContainer.classList.remove("active");
        chatbotToggle.style.display = "flex";  // Show toggle button when chat is contracted
    } else if (saveState === "minimized") {
        chatContainer.classList.remove("active");
        chatbotToggle.style.display = "flex";  // Show toggle button when minimized
    } else if (saveState === "closed") {
        chatContainer.style.display = "none";  // Hide chat completely
        chatbotToggle.style.display = "flex";  // Show toggle button when chat is closed
    }
}

window.onload = function () {
    checkState();  // Check the chat state on page load
};

function loadChatHistory() {
    const chatBox = document.getElementById("chatBox");
    const chatHistory = JSON.parse(sessionStorage.getItem("chatHistory")) || [];

    console.log("Loaded chat history:", chatHistory);  // Debugging line

    if (chatHistory.length === 0) {
        console.log("No chat history found in sessionStorage.");
    }

    chatHistory.forEach(entry => {
        addMessage(entry.question, "user");
        addMessage(entry.answer, "bot");
    });

    scrollToBottom();
}

async function sendMessage() {
    const userInput = document.getElementById("userInput");
    const question = userInput.value.trim();

    const chatHistory = JSON.parse(sessionStorage.getItem("chatHistory")) || [];
    // alert("Chat history: " + JSON.stringify(chatHistory)); // Convert the array to a string before displaying

    if (!question) {
        console.warn("No question entered!");
        return;
    }

    console.log("User question in sendMessage:", question);

    // Add user message to chat UI
    addMessage(question, "user");
    userInput.value = ""; // Clear input field after sending message

     // Disable input field while waiting for response
    userInput.disabled = true;
    userInput.classList.add("thinking-placeholder");
    userInput.placeholder = "Bot is thinking...";


    try {
        if (!jwtToken) {
            alert("You are not logged in. Please log in first.");
            return;
        }
        const response = await fetch("http://127.0.0.1:5000/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${jwtToken}` // Include the token in the Authorization header
                // "X-API-KEY": API_KEY // Include the API key in the headers
            },
            credentials: "include", 
            body: JSON.stringify({ question: question, chatHistory: chatHistory })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error("Server Error:", errorText);
            throw new Error(`Server returned ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        if (data.answer) {
            let botMessage = data.answer;
            if (data.document_path) {
                botMessage += `<br><a href="${data.document_path}" target="_blank">View Document</a>`;
            }
            addMessage(botMessage, "bot");
            updateChatHistory(question, botMessage);
        } else {
            addMessage("No response from the bot.", "bot");
        }
    } catch (error) {
        console.error("Fetch Error:", error);
        addMessage("Error connecting to the server.", "bot");
    }
    userInput.disabled = false; // Re-enable input field after response
    userInput.classList.remove("thinking-placeholder");
    userInput.placeholder = "Ask a question..."; // Reset placeholder text

}


function addMessage(text, sender) {
    const chatBox = document.getElementById("chatBox");
    const messageId = `bot-msg-${Date.now()}`;

    if (sender === "bot") {
        // Outer wrapper to contain message and copy button
        const wrapper = document.createElement("div");
        wrapper.classList.add("bot-message-wrapper");
        wrapper.style.position = "relative"; // Enable absolute positioning inside

        // Message div
        const messageDiv = document.createElement("div");
        messageDiv.id = messageId;
        messageDiv.classList.add("message", "bot-message");
        messageDiv.innerHTML = `<img src="https://systems-plus.com/wp-content/themes/systemsplus/favicon.png" class="logo">${text}`;

        // Feedback container
        const feedbackContainer = document.createElement("div");
        feedbackContainer.classList.add("feedback-container");
        feedbackContainer.innerHTML = `
            <button class="feedback-button thumbs-up">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v10h12l2-7v-1a2 2 0 0 0-2-2h-5z"></path>
                </svg>
            </button>
            <button class="feedback-button thumbs-down">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10 15v4a3 3 0 0 0 3 3l4-9V3H5l-2 7v1a2 2 0 0 0 2 2h5z"></path>
                </svg>
            </button>
        `;
        messageDiv.appendChild(feedbackContainer);

        // Copy button
        const copyButton = document.createElement("button");
        copyButton.classList.add("copy-button");
        copyButton.setAttribute("onclick", `copyToClipboard('${messageId}')`);
        copyButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" height="20" width="20" viewBox="0 0 24 24"
                 fill="none" stroke="#888888" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                 class="feather feather-copy">
                <path d="M16 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2z"/>
                <rect x="9" y="2" width="6" height="4" rx="1" ry="1"/>
            </svg>
        `;

        copyButton.style.position = "absolute";
        copyButton.style.bottom = "8px";
        copyButton.style.right = "-10px"; // adjust as needed to place outside message box

        // Build DOM
        wrapper.appendChild(messageDiv);
        wrapper.appendChild(copyButton);
        chatBox.appendChild(wrapper);
    } else {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "user-message");
        messageDiv.textContent = text;
        chatBox.appendChild(messageDiv);
        scrollToBottom();
    }
    const chatHistory = JSON.parse(sessionStorage.getItem("chatHistory"))
    if (chatHistory && chatHistory.length > 0) {
        scrollPartiallySmooth(200); // Scroll down smoothly after adding a message  
       
    }else {
        return;
    }
    
}

function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    const textToCopy = element.innerText || element.textContent;

    navigator.clipboard.writeText(textToCopy).then(() => {
        // alert("Answer copied to clipboard!");
    }).catch(err => {
        console.error("Copy failed:", err);
        alert("Failed to copy text.");
    });
}


//  Fix: Properly Add Messages to Chat
// function addMessage(text, sender) {
//     const chatBox = document.getElementById("chatBox");
//     const messageDiv = document.createElement("div");
//     messageDiv.classList.add("message", sender === "user" ? "user-message" : "bot-message");

//     if (sender === "bot") {
//         messageDiv.innerHTML = `<img src="https://systems-plus.com/wp-content/themes/systemsplus/favicon.png" class="logo">${text}
           
//         `;

//         // Append bot message
//         chatBox.appendChild(messageDiv);

//         // Create feedback container separately
//         const feedbackContainer = document.createElement("div");
//         feedbackContainer.classList.add("feedback-container");
//         feedbackContainer.innerHTML = `
// 			<button class="feedback-button thumbs-up">
// 				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
// 					<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v10h12l2-7v-1a2 2 0 0 0-2-2h-5z"></path>
// 				</svg>
// 			</button>
// 			<button class="feedback-button thumbs-down">
// 				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
// 					<path d="M10 15v4a3 3 0 0 0 3 3l4-9V3H5l-2 7v1a2 2 0 0 0 2 2h5z"></path>
// 				</svg>
// 			</button>
//         `;

//         // Append feedback container after bot message
//         chatBox.appendChild(feedbackContainer);
//     } else {
//         messageDiv.textContent = text;
//         chatBox.appendChild(messageDiv);
//     }

//     scrollToBottom();
// }


//  Ensure Chat History is Updated
function updateChatHistory(question, answer) {
    console.log("Question:", question);  // Check if question is being passed correctly
    console.log("Answer:", answer);   
    const chatHistory = JSON.parse(sessionStorage.getItem("chatHistory")) || [];
    chatHistory.push({ question, answer });
    sessionStorage.setItem("chatHistory", JSON.stringify(chatHistory));
}

//  Scroll Chat to Bottom
function scrollToBottom() {
    const chatBox = document.getElementById("chatBox");
    chatBox.scrollTop = chatBox.scrollHeight;
}

function scrollPartiallySmooth(pixels = 50) {
    const chatBox = document.getElementById("chatBox");
    chatBox.scrollBy({
        top: pixels,
        behavior: "smooth"
    });
}

//  Debugging: Ensure Fetch Requests Are Sent
document.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
        e.preventDefault();  // Prevent the form from submitting when "Enter" is pressed
        sendMessage();
    }
});

// Function to toggle between default and expanded sizes
function toggleChatSize() {
    const chatWindow = document.querySelector('.chat-container');
    chatWindow.classList.toggle('expanded');
	 if (chatWindow) {
        chatWindow.classList.toggle("fullscreen");
    }
    const togglePath = document.getElementById("toggle-path");

    if (chatWindow.classList.contains("fullscreen")) {
        togglePath.setAttribute("d", "M10 8l4 4-4 4");
    }
    else {   
        togglePath.setAttribute("d", "M14 8l-4 4 4 4");
    }
}


//  Apply Chatbot Styles (No Change)
const style = document.createElement("style");
style.innerHTML = `
    body {
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 0;
        background-color: #f4f4f4;
    }
    .chatbot-toggle {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        font-size: 30px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.2);
    }
    // .chat-container {
        // display: none;
        // position: fixed;
        // bottom: 90px;
        // right: 20px;
        // width: 350px;
        // max-width: 90%;
        // background: white;
        // border-radius: 10px;
        // box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
        // overflow: hidden;
        // transform: scale(0);
        // transition: transform 0.3s ease-in-out;
    // }
	.chat-container {
         display: none;
         position: fixed;
         bottom: 10%;
         right: 5%;
         width: 30%;
         max-width: 90%;
         max-height: 80%;
         background: white;
         border-radius: 10px;
         box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
         overflow: hidden;
         transform: scale(0);
         transition: transform 0.3s ease-in-out;
     }
    .chat-container.active {
        display: block;
        transform: scale(1);
    }
    .chat-header {
        background-color: #fafafa;
        color:#00b0ea;
        padding: 15px;
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        flex-wrap: wrap; /* Prevent overlap by allowing buttons to wrap */
    }
    .chat-box {
        flex:1;
        height: 300px;
        overflow-y: auto;
        padding: 15px;
        background: #fff;
        fdisplay: flex;
        flex-direction: column;
        gap: 10px;
        display: flex;
    }
    .message {
    display: flex;
        padding: 10px;
        margin: 5px;
        border-radius: 8px;
        max-width: 80%;
        word-wrap: break-word;
    }
       .user-message {
		background: #2F3146;
		color: white;

		justify-content: flex-end;
		text-align: right;
		display: inline-block; /* Makes the div wrap around the text */
		max-width: 80%; /* Prevents it from stretching too wide */
		word-wrap: break-word; /* Ensures long words wrap properly */
		padding: 10px;
		/*margin: 5px;*/
		border-radius: 8px;
		font-size: 16px;
		line-height: 1.4;
		white-space: pre-wrap; /* Preserves spaces and line breaks */
        width:fit-content; /* Adjusts width to fit content */
        margin-left: auto !important; /* Aligns to the right */
	}
   
 
    .bot-message {
        background: #f1f1f1;
        color: black;
        align-self: flex-start;
        text-align: left;        
        max-width: 80%;
        word-wrap: break-word;
        padding: 10px;
        margin: 5px 10px;
        border-radius: 8px;
        font-size: 16px;
        white-space: pre-wrap;
		display: flex;
        flex-direction: column;        
    }
   
    .chat-input {
        display: flex;
        border-top: 1px solid #ddd;
        padding: 10px;
        background: white;
        width: auto;
        // border: 1px red solid;
        align-items: center;
    }
    .chat-input form {
    display: flex;
        width: 100% !important;
    }
    .chat-input input {
        flex: 1;
        padding: 10px;
        border: none;
        border-radius: 5px;
        outline: none;
        font-size: 14px;
        width: 80%;
        // border: 1px blue solid;
    }
    .chat-input button {
        padding: 10px 15px;
        border: none;
        background: #007bff;
        color: white;
        border-radius: 5px;
        cursor: pointer;
        margin-left: 5px;
    }
    .chat-input button:hover {
        background: #0056b3;
    }
    .logo {
        margin-right: 10px;
    }



 .minimize-btn,
        .close-btn {
            background: none;
            border: none;
            color: #007bff;
            font-size: 20px;
            cursor: pointer;
        }

        .minimize-btn:hover,
        .close-btn:hover {
            color: #0056b3;
        }

        .chat-header div {
            display: flex;
            justify-content: flex-start;
            gap: 10px;
        }
		.message-content {
			display: flex;
			align-items: center;
			gap: 10px;
		}

		.feedback-container {
			display: flex;
			gap: 0px;
			justify-content: flex-start;
			margin-top: 10px;
			margin-left: 10px;
		}
		.feedback-button {
			background: transparent;
			border: none; /* Outlined border */
			border-radius: 8px; /* Rounded edges */
			padding: 6px;
			cursor: pointer;
			transition: all 0.3s ease-in-out;
			display: flex;
			align-items: center;
			justify-content: center;
			width: 36px;
			height: 36px;
		}
		.feedback-button svg {
			stroke: #666; /* Default gray color */
			width: 20px;
			height: 20px;
			transition: stroke 0.3s ease-in-out;
		}
			
		.logo {
			width: 15px;
			height: 15px;
		}
		.chat-input button:hover {
		    color: #19C37D; /* ChatGPT's green highlight */
		}

		.chat-input #voiceButton i {
			font-size: 20px;
		}
		.chat-input #voiceButton {
		    padding: 6px;
			border-radius: 12px;
		}
		.chat-container.expanded {
			width: 90%;
			height: 90%;
			right: 5%;
			bottom: 5%;
		}
		.minimize-btn, .expand-btn {
			background: none;
			border: none;
			font-size: 16px;
			cursor: pointer;
		}
		.chat-controls {
			display: flex;
			justify-content: space-between;
			background-color: #ddd;
			padding: 5px;
            flex-wrap: wrap; /* Prevent overlap by allowing buttons to wrap */
		}
        .center-text {
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            font-size: 12px;
            color: gray;
        }
		.chat-container.fullscreen .bot-message {
			max-width: 90%; /* Allow full expansion */
		}
		.chat-container.fullscreen {
			width: 90%;
			height: 80%;
			position: fixed;
			top: 5%;
			left: 5%;
			z-index: 999;
			border-radius: 10px;
			box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-direction: column; !important
		}
		.user-message, .bot-message {
			display: block; /* Ensures each message takes full width */
			padding: 10px;
			border-radius: 8px;
			margin: 5px 10px;
			max-width: 80%;
			word-wrap: break-word;
		}
		.chat-container.fullscreen .bot-message,
		.chat-container.fullscreen .user-message {
			max-width: 90%;
		}

    .copy-button {
        position: absolute; !important
        margin-top: 5px;
        padding: 4px 8px;
        font-size: 12px;
        cursor: pointer;
        border: none;
        border-radius: 5px;
        }
    .copy-button-wrapper {
        position: relative;
        bottom: 5px;
        right: 5px;
}
  #toggle-btn {
  position: relative;
  top: 0px;
  left: -21px; /* Half outside the container */
  
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  outline: none;
  z-index: 20; /* Ensure it stays above */
  border-radius: 50%; /* optional: make it rounded */
 
}

#toggle-btn svg {
  display: block;
}




@media (max-width: 600px) {
        .chat-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .chat-controls {
        justify-content: flex-start;
        width: 100%;
    }

    .minimize-btn,
    .expand-btn {
        font-size: 20px;
    }

    .chat-input {
        flex-direction: column; /* Stack input and buttons vertically on smaller screens */
        align-items: stretch; /* Ensure input and buttons stretch to full width */
    }

    /* Form inside Chat Input - Stack items vertically */
    .chat-input form {
        flex-direction: column; /* Stack input and buttons vertically */
        width: 100%;
    }

    .chat-input input {
        margin-right: 0; /* Remove right margin when stacking vertically */
        margin-bottom: 10px; /* Add space below the input field */
    }

    .chat-input button {
        margin-left: 0; /* Remove left margin when stacking vertically */
        margin-bottom: 10px; /* Add space below buttons */
    }
}

/* For medium screens (e.g., tablets) */
@media (min-width: 600px) and (max-width: 1024px) {

.chat-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .chat-controls {
        justify-content: flex-start;
        width: 100%;
    }

    .minimize-btn,
    .expand-btn {
        font-size: 20px;
    }
    .chat-input {
        justify-content: space-between; /* Ensure space between input and buttons */
    }
}

/* For larger screens (e.g., desktops) */
@media (min-width: 1024px) {

.chat-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .chat-controls {
        justify-content: flex-start;
        width: 100%;
    }

    .minimize-btn,
    .expand-btn {
        font-size: 20px;
    }
    .chat-input {
        justify-content: space-between; /* Ensure space between input and buttons */
    }
}
       
`
;
document.head.appendChild(style);

function reloadDocuments() {
    fetch("http://127.0.0.1:5000/reload_documents", {
        method: "GET"
        // headers: {
        //     "X-API-KEY": API_KEY // Include the API key in the headers
        // }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to reload documents.');
        }
        return response.json();
    })
    .then(data => {
        console.log("Documents reloaded successfully:", data);
        alert(`Documents reloaded successfully. Total documents: ${data.documents_count}`);
    })
    .catch(error => {
        console.error("Error reloading documents:", error);
        alert("Error reloading documents.");
    });
}


