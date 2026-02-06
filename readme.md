# HTML and JavaScript Chatbot UI

This project provides the frontend UI for an AI chatbot, built using HTML, CSS, and JavaScript. It's designed to be used with a backend that handles the chatbot's logic and document processing.

## Features

* **Floating Chatbot Button:** A fixed button on the screen to toggle the chatbot window.
* **Toggleable Chat Window:** The chatbot window can be shown or hidden with a click.
* **Dynamic Chat Interface:** The chat interface is generated dynamically using javascript.
* **Styled Chat Messages:** User and bot messages are styled differently for easy distinction.
* **Chat Input Area:** An input field and send button for users to type their messages.
* **Chat History Rendering:** renders the chat history from the backend.
* **Logo Display:** Displays a logo in the bot's messages.

## Technologies Used

* **HTML:** For the structure of the chatbot UI.
* **CSS:** For styling the chatbot UI.
* **JavaScript:** For handling user interactions, dynamic UI updates, and communication with the backend.

## Setup and Installation

1.  **HTML File:**
    * Create an HTML file (e.g., `index.html`) and copy the provided HTML code into it.
2.  **JavaScript File:**
    * Create a JavaScript file (e.g., `script.js`) and copy the provided JavaScript code into it.
3.  **Link JavaScript:**
    * In your HTML file, add the following line before the closing `</body>` tag to link the JavaScript file:

        ```html
        <script src="js/main.js"></script>
        ```

4.  **Backend Integration:**
    * Ensure that your backend is running and accessible from the browser.
    * Make sure the backend supports the `/chat` endpoint for sending user messages.
    * Install backend code and add it in startup to execute.

## Usage

1.  **Open HTML:** Open the HTML file in a web browser.
2.  **Toggle Chatbot:** Click the floating chatbot button to open or close the chat window.
3.  **Send Messages:** Type your message in the input field and click the "Send" button.
4.  **View Responses:** The bot's responses will appear in the chat box.

## Code Structure

* **`index.html`:** Contains the HTML structure for the chatbot UI.
* **`main.js`:** Contains the JavaScript logic for handling user interactions, updating the UI, and communicating with the backend.

## Important Notes

* **Backend Integration:** This project is only the frontend UI. You'll need a backend to handle the chatbot's logic and document processing.
* **CORS:** If your backend is running on a different origin than your HTML file, you may encounter CORS issues. Make sure your backend is configured to handle CORS requests.
* **Customization:** You can customize the styles and functionality of the chatbot UI by modifying the HTML, CSS, and JavaScript code.
* **Chat History:** The chat history is retrieved from the HTML element with the id of 'chat-history-data', and then rendered by javascript.


# tO RUN CODE
uvicorn main:asgi_app --host 127.0.0.1 --port 5000
tasklist | findstr "uvicorn"
stop-process -Id 30488
