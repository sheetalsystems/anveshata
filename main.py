# main.py - Segment 1: Imports and App Setup
from flask import Flask, jsonify, render_template, request, session, send_file
from asgiref.wsgi import WsgiToAsgi
import os, io
import secrets
from flask_cors import CORS
from datetime import timedelta, datetime
import jwt
from functools import wraps
from flask import send_from_directory
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from src.document_processing import load_documents, query_agent
from src.user_authentication import get_users_from_json, jwt_required, save_token_to_file,load_token_from_file
from src.pdf_generation import simpleSplit
from src.config import DOCUMENTS_FOLDER, USERS_JS_PATH, TOKEN_EXPIRY, TOKEN_FILE, CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID

# For SharePoint URL
import asyncio
import requests
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient

#for sharepoint url
from src.onedrive_integration import download_sharepoint_files, load_graphtoken_from_file
import uvicorn

app = Flask(__name__)
CORS(app,supports_credentials=True)
app.secret_key = '323575946e772ccc0069a494b01e1c27'

#onedrive code
#------------------------------------------------------------------------

first_request_done = False # Add a flag to track first request
document_loading_task= None # Initialize the task variable
async def async_load_documents():
    """Loads documents from SharePoint into memory before the first request."""
    await load_documents(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID)
    print("Initial document loading complete.")

@app.before_request
async def setup_documents():
    """Sets up the document cache before the first request."""
    global first_request_done, document_loading_task
    if not first_request_done:
        print("Starting initial document loading...")
        if document_loading_task is None:
            document_loading_task = asyncio.create_task(async_load_documents())
        await document_loading_task
        first_request_done = True
        print("Document cache setup complete.")


# @app.route('/query', methods=['POST'])
# async def query():
#     """Handles user queries and returns AI agent responses, integrated with session-based chat history."""
#     try:
#         print(f"Session at the beginning of /query: {session}")
#         data = request.get_json()
#         if not data or "question" not in data:
#             return jsonify({"error": "Invalid request, 'question' key missing"}), 400

#         question = data["question"]

#         # Get chat history from session
#         chatHistory = data.get("chatHistory", [])
#         print(f"Chat history in /query (before call): {chatHistory}")

#         # SharePoint Folder Access
#         folder_path = "/NBDocPOC/DocPDFIMG:"
#         tenant_id = TENANT_ID
#         client_id = CLIENT_ID
#         client_secret = CLIENT_SECRET
#         scopes = ["Sites.Selected"]

#         api_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:{folder_path}/children"
#         access_token = GRAPH_ACCESS_TOKEN

#         headers = {
#             "Authorization": f"Bearer {access_token}",
#             "Content-Type": "application/json",
#         }

#         response = requests.get(api_url, headers=headers)
#         response.raise_for_status()
#         folder_contents = response.json()

#         if folder_contents and folder_contents.get("value"):
#             print("SharePoint folder contents:")
#             for item in folder_contents["value"]:
#                 print(f"- {item.get('name')}")
#         else:
#             print("SharePoint folder is empty or not found.")
#         print("Finished SharePoint folder access")

#         # Call AI agent
#         print("Calling query_agent...")
#         answer, input_tokens, output_tokens, response_time, document_path = await query_agent(
#             question, client_id, client_secret, tenant_id, SHAREPOINT_SITE_ID, chatHistory
#         )
#         print(f"Returned from query_agent - answer: {answer}, type(answer): {type(answer)}")

#         # Construct document URL
#         document_url = f"http://127.0.0.1:5000/DocPDFIMG/{os.path.basename(document_path)}" if document_path else None

#         # Initialize chat history in session if not exists
#         if 'chatHistory' not in session:
#             session['chatHistory'] = []
#             print("Chat history initialized in session")

#         # Append new Q&A to session history
#         session['chatHistory'].append({
#             "question": question,
#             "answer": answer,
#             "document_path": document_url
#         })
#         session.modified = True  # Save session changes

#         print(f"Updated chat history: {session['chatHistory']}")

#         return jsonify({
#             "answer": answer,
#             "input_tokens": input_tokens,
#             "output_tokens": output_tokens,
#             "response_time": response_time,
#             "document_path": document_url
#         })

#     except Exception as e:
#         print(f"Error accessing SharePoint folder or querying agent: {e}")
#         return jsonify({"error": f"Internal Server Error: {e}"}), 500
    
@app.route('/query', methods=['POST'])
@jwt_required
def query():
    """Handles user queries and returns AI agent responses."""
    data = request.get_json()
    question = data.get('question')
    chatHistory = data.get('chatHistory', [])
    print(f"Received question: {question}")
    # SharePoint Folder Access Logic
    folder_path = "/NBDocPOC/DocPDFIMG:"  # Replace with the correct path
    tenant_id = TENANT_ID
    client_id = CLIENT_ID
    client_secret = CLIENT_SECRET
    scopes = ["Sites.Selected"]

    try:
        #credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        #graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

        api_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:{folder_path}/children"
        #access_token = (await credential.get_token("https://graph.microsoft.com/.default")).token #added await
        # access_token = GRAPH_ACCESS_TOKEN
        access_token = load_graphtoken_from_file()
        if not access_token:
            return jsonify({"error": "Graph token missing or invalid."}), 401

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        folder_contents = json.loads(response.text)

        if folder_contents and folder_contents.get("value"):
            print("SharePoint folder contents:")
            for item in folder_contents["value"]:
                print(f"- {item.get('name')}")
        else:
            print("SharePoint folder is empty or not found.")
        print("Finished SharePoint folder access")
        # Integrate with query_agent
        print("Calling query_agent...")
        answer, input_tokens, output_tokens, response_time, document_path = asyncio.run(query_agent(question, CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID, chatHistory)) #added await
        print(f"Returned from query_agent - answer: {answer}, type(answer): {type(answer)}")
        
         # Construct document URL
        document_url = f"http://127.0.0.1:5000/DocPDFIMG/{os.path.basename(document_path)}" if document_path else None

         # Initialize chat history in session if not exists
        if 'chatHistory' not in session:
            session['chatHistory'] = []
            print("Chat history initialized in session")

        # Append new Q&A to session history
        session['chatHistory'].append({
            "question": question,
            "answer": answer,
            "document_path": document_url
        })
        session.modified = True  # Save session changes

        
        response = {
            'answer': answer,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'response_time': response_time,
            'document_path': document_url
        }
        print(f"Returning response: {response}")
        return jsonify(response)

    except Exception as e:
        print(f"Error accessing SharePoint folder: {e}")
        return jsonify({"error": f"Error accessing SharePoint folder: {e}"}), 500
#-------------------------------------------------------------------------------    

# Load documents when the Flask app starts
#load_documents(DOCUMENTS_FOLDER)

# main.py - Segment 2: Login Route
@app.route('/login', methods=['POST']) 
def login():
    """Handles user login and JWT token generation."""
    try:
        data = request.get_json()
        if not data or "username" not in data or "password" not in data:
            return jsonify({"error": "Username and password are required"}), 400

        username, password = data["username"], data["password"]
        users = get_users_from_json(USERS_JS_PATH)

        valid_user = any(user for user in users if user["username"] == username and user["password"] == password)

        if not valid_user:
            return jsonify({"error": "Invalid username or password"}), 401

        token = jwt.encode(
            {"username": username, "exp": datetime.utcnow() + TOKEN_EXPIRY},
            app.secret_key,
            algorithm="HS256"
        )
        save_token_to_file(token)
        
        return jsonify({"token": token}), 200

    except Exception as e:
        print(f"Error during login: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# main.py - Segment 3: Document Serving and Chat Routes
@app.route('/DocPDFIMG/<path:filename>')
def documents(filename):
    """Serves files from the DOCUMENTS_FOLDER."""
    return send_from_directory(DOCUMENTS_FOLDER, filename)

@app.route('/chat', methods=['POST'])
@jwt_required
def chat():
    """Handles chat queries and returns answers."""
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Invalid request, 'question' key missing"}), 400

        question = data["question"]
        chat_history = session.get("chat_history", []) # Get history from session
        answer, input_tokens, output_tokens, response_time, document_path = query_agent(question, DOCUMENTS_FOLDER, chat_history)

        if isinstance(answer, str) and (answer.startswith("An error occurred:") or 
                                       answer.startswith("Could not generate embedding for the question.") or 
                                       answer.startswith("No documents found in the folder.")):
            return jsonify({"error": answer}), 500

        document_url = f"http://127.0.0.1:5000/DocPDFIMG/{os.path.basename(document_path)}" if document_path else None

        #chat_history = session.get("chat_history", [])
        chat_history.append({'question': question, 'answer': answer, 'document_path': document_url})
        session['chat_history'] = chat_history

        return jsonify({
            "answer": answer,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "response_time": response_time,
            "document_path": document_url
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

# main.py - Segment 4: Test and PDF Download Routes (Corrected)
@app.route('/test', methods=['GET'])
def test():
    """Tests if the Flask app is running."""
    return jsonify({"message": "Flask app is running"})

@app.route('/download_pdf', methods=['GET'])
@jwt_required 
def download_pdf():
    """Downloads chat history as a PDF."""
    chat_history = session.get("chat_history", [])
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    left_margin = 50
    right_margin = 50
    bottom_margin = 50
    max_width = width - (left_margin + right_margin)
    y = height - 80
    page_number = 1
    first_page = True

    # Define header and footer functions here, before they are called
    def add_header():
        pdf.setFont("Helvetica-Bold", 14)
        title = "Document-Based Q&A"
        pdf.drawString((width - pdf.stringWidth(title, "Helvetica-Bold", 14)) / 2, height - 50, title)

    def add_footer():
        pdf.setFont("Helvetica", 10)
        pdf.drawString(width / 2 - 20, bottom_margin / 2, f"Page {page_number}")

    add_header()
    pdf.setFont("Helvetica", 12)

    for entry in chat_history:
        if y < bottom_margin + 40:
            add_footer()
            pdf.showPage()
            page_number += 1
            pdf.setFont("Helvetica", 12)
            y = height - 80

        question_lines = simpleSplit(f"Q: {entry['question']}", "Helvetica", 12, max_width)
        for line in question_lines:
            if y < bottom_margin + 40:
                add_footer()
                pdf.showPage()
                page_number += 1
                pdf.setFont("Helvetica", 12)
                y = height - 80

            pdf.drawString(left_margin, y, line)
            y -= 20

        answer_lines = simpleSplit(f"A: {entry['answer']}", "Helvetica", 12, max_width)
        for line in answer_lines:
            if y < bottom_margin + 40:
                add_footer()
                pdf.showPage()
                page_number += 1
                pdf.setFont("Helvetica", 12)
                y = height - 80

            pdf.drawString(left_margin + 20, y, line)
            y -= 20

        y -= 20

    add_footer()
    pdf.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="AI_agent.pdf", mimetype="application/pdf")

# main.py - Segment 5: Index and Reload Routes
@app.route("/", methods=["GET", "POST"])
def index():
    """Renders the main page and handles chat interactions."""
    session.setdefault("chat_history", [])

    if request.method == "POST":
        question = request.form.get("question")
        if question:
            answer, _, _, _, document_path = query_agent(question, DOCUMENTS_FOLDER)
            document_url = f"http://127.0.0.1:5000/DocPDFIMG/{os.path.basename(document_path)}" if document_path else None
            session["chat_history"].append({"question": question, "answer": answer, "document_path": document_url})
            session.modified = True

    return render_template("index.html", chat_history=session["chat_history"])

@app.route('/reload_documents', methods=['GET'])
def reload_documents():
    """Reloads documents from the DOCUMENTS_FOLDER."""
    try:
        documents = load_documents(DOCUMENTS_FOLDER)
        return jsonify({"message": "Documents reloaded successfully", "documents_count": len(documents)}), 200
    except Exception as e:
        print(f"Error reloading documents: {str(e)}")
        return jsonify({"error": f"Failed to reload documents: {str(e)}"}), 500
    
# main.py - Segment 6: List Documents and Main Execution
@app.route('/list_documents', methods=['GET'])
def list_documents():
    """Lists all documents in the DOCUMENTS_FOLDER."""
    try:
        if not os.path.exists(DOCUMENTS_FOLDER):
            return jsonify({"error": "Documents folder not found"}), 404

        files = [f for f in os.listdir(DOCUMENTS_FOLDER) if f.lower().endswith((".pdf", ".docx"))]
        if not files:
            return jsonify({"message": "No documents found in the folder"}), 200

        document_links = [{"filename": file, "url": f"http://127.0.0.1:5000/static/{file}"} for file in files]
        return jsonify({"documents": document_links}), 200

    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
    
@app.route('/get_token', methods=['GET'])
def get_token():
    """Endpoint to fetch the token."""
    token = load_token_from_file()
    if token:
        try:
            # Validate the token before returning it
            jwt.decode(token, app.secret_key, algorithms=["HS256"])
            return jsonify({"token": token}), 200
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
    return jsonify({"error": "Token not found"}), 404

#if __name__ == "__main__":
#    app.run(debug=True)

asgi_app = WsgiToAsgi(app) #Wrap the flask app.

if __name__ == "__main__":
    import  uvicorn
    uvicorn.run(asgi_app, host="127.0.0.1", port=5000)