# main.py - Segment 1: Imports and App Setup
# test commit chat history
import sys
import traceback
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
import datetime

from src.document_processing import load_documents, load_or_build_faiss_hnsw_index,query_agent_with_faiss_hnsw
#from src.document_processing_fastembed import load_documents, query_agent
from src.user_authentication import get_users_from_json, jwt_required, save_token_to_file,load_token_from_file
from src.pdf_generation import simpleSplit
from src.config import AUTHORITY,SCOPE,DOCUMENTS_FOLDER, USERS_JS_PATH, TOKEN_EXPIRY, TOKEN_FILE, CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID,SHAREPOINT_DRIVE_ID, APP_SECRET_KEY, ONED_DOCUMENT_URL, APP_HOST, APP_PORT, SSL_KEYFILE, SSL_CERTFILE, IS_SECURE, CROS_ORIGINS, ONED_DOCUMENT_URL_QUERY,GRAPH_TOKEN_FILE,REDIRECT_URI


# For SharePoint URL
import asyncio
import requests
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient

#for sharepoint url
from src.onedrive_integration import download_sharepoint_files, load_graphtoken_from_file
import uvicorn

from flask import Flask, redirect, session, request, url_for, render_template, jsonify
from msal import ConfidentialClientApplication



CHAT_HISTORY_DIR = "chat_history"
os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)

def resource_path(relative_path):
    """
    Get absolute path to resource, works in dev and PyInstaller exe.
    """
    if getattr(sys, 'frozen', False):  # Running as exe
        base_path = os.path.dirname(sys.executable)
    else:  # Running as script
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

app = Flask(
    __name__,
    static_folder=resource_path("static")
)

app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",     # Use "None" only if you're running over HTTPS
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True # Set to True in production with HTTPS
)

CORS(app,
     supports_credentials=True, 
     origins=CROS_ORIGINS,
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])
app.secret_key = APP_SECRET_KEY

#onedrive code
#------------------------------------------------------------------------

first_request_done = False # Add a flag to track first request
document_loading_task= None # Initialize the task variable

@app.before_request
async def setup_documents():
    """Sets up the document cache before the first request."""
    global first_request_done, document_loading_task
    if not first_request_done:
        print("Starting initial document loading...")
        if document_loading_task is None:
            document_loading_task = asyncio.create_task(
                load_or_build_faiss_hnsw_index(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID)
            )
        await document_loading_task
        first_request_done = True
        print("Document cache setup complete.")
        
 


def save_graph_token_to_file(token):
    try:
        with open(GRAPH_TOKEN_FILE, "w") as f:
            json.dump({"graph_token": token}, f)
            print("Graph token saved to file.")
    except Exception as e:
        print(f"Error saving token: {e}")

def load_graph_token_from_file():
    try:
        if os.path.exists(GRAPH_TOKEN_FILE):
            with open(GRAPH_TOKEN_FILE, "r") as f:
                data = json.load(f)
                return data.get("graph_token")
        else:
            print("graph_token.json not found.")
            return None
    except Exception as e:
        print(f"Error loading graph token: {e}")
        return None   
        
          
def build_msal_app(cache=None):
    return ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache
    )

def build_auth_url():
    return build_msal_app().get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    
    
@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))  # redirect to login if not logged in
    return render_template("chatbot.html", user=session["user"])


@app.route("/login")
def login():
    auth_url = build_auth_url()
    return redirect(auth_url)

# for SSO dynamic graph token retrieval
@app.route("/get_data")  
def authorized():
    if "code" not in request.args:
        return "Login failed. No code returned.", 400

    msal_app = build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        request.args["code"],
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    
    if "id_token_claims" in result:
        user_info = result["id_token_claims"]
        user_id = user_info.get("oid")  # This is the stable unique ID

        if not user_id:
            return "Login failed: No user ID (oid) found in token.", 400
        
        
        session["user"] = user_info
        session["user_id"] = user_id  # Optional convenience
        session["access_token"] = result["access_token"]
        # session.modified = True  # force Flask to save session
        
        print(" Login successful for user ID:", user_id)
        print(" Session AFTER LOGIN:", dict(session))
        
        
        save_graph_token_to_file(result["access_token"])

        return redirect(url_for("home"))  # or your desired frontend route

    else:
        return f"Login error: {result.get('error_description')}", 400
  

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('home', _external=True)}"
    )    
       


# def load_user_history(user_id):
#     file_path = os.path.join(CHAT_HISTORY_DIR, f"{user_id}.json")
#     if os.path.exists(file_path):
#         with open(file_path, "r", encoding="utf-8") as f:
#             return json.load(f)
#     return []


def load_chat_history_from_sharepoint(user_id, access_token):
    """Load existing chat history from SharePoint for the given user_id."""
    url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drives/{SHAREPOINT_DRIVE_ID}/root:/chat-history/{user_id}.json:/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        try:
            data = json.loads(resp.text)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]  # wrap single object into a list
            else:
                print(" Existing history is not a list or dict. Resetting to empty list.")
                return []
        except json.JSONDecodeError:
            print(" Error decoding existing chat history JSON.")
            return []
    elif resp.status_code == 404:
        return []
    else:
        print(f" Failed to load chat history: {resp.status_code} - {resp.text}")
        return []
    
    
       
@app.route("/chat-history", methods=["GET"])
def get_chat_history():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "User not logged in"}), 401

        access_token = load_graphtoken_from_file()
        if not access_token:
            return jsonify({"error": "Graph token missing or invalid"}), 401

        history = load_chat_history_from_sharepoint(user_id, access_token)
        return jsonify(history)

    except Exception as e:
        print("Error fetching chat history:", str(e))
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500




@app.route('/query', methods=['POST'])
def query():
    try:
        print(" Current working directory:", os.getcwd())
        print(" Full session object:", dict(session))

        user_info = session.get("user")
        user_id = session.get("user_id")

        if not user_info:
            print(" No 'user' key in session.")
        else:
            print(" 'user' found in session:", user_info)

        if not user_id:
            print(" 'user_id' not found in session.")
        else:
            print(" 'user_id' found in session:", user_id)

        data = request.get_json()
        question = data.get('question')
        chatHistory = data.get('chatHistory', [])
        print(f" Received question: {question}")

        folder_path = "/NBDocPOC/DocPDFIMG:"  # For initial SharePoint folder test

        # Load Microsoft Graph access token
        access_token = load_graphtoken_from_file()
        if not access_token:
            print(" Graph token missing or invalid.")
            return jsonify({"error": "Graph token missing or invalid."}), 401

        # Check SharePoint folder exists (optional)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        api_url = f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive/root:{folder_path}/children"
        try:
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            print(f" SharePoint access error: {http_err}")
            return jsonify({"error": f"Graph API access denied: {response.text}"}), 401

        # 🔍 Query agent logic
        try:
            answer, input_tokens, output_tokens, response_time, document_path, follow_up_required, relevant_document_found = asyncio.run(
                query_agent_with_faiss_hnsw(
                    question, CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID, chatHistory
                )
            )
        except Exception as e:
            print(" Exception in query_agent_with_faiss_hnsw:", str(e))
            traceback.print_exc()
            return jsonify({"error": "Error generating response from AI model."}), 500

        # 📎 Build document link
        document_url = (
            f"{ONED_DOCUMENT_URL}/{os.path.basename(document_path)}?{ONED_DOCUMENT_URL_QUERY}"
            if document_path and not follow_up_required and relevant_document_found
            else None
        )

        # Update session
        session.setdefault('chatHistory', []).append({
            "question": question,
            "answer": answer,
            "document_path": document_url
        })
        session.modified = True

        #  Upload chatHistory to SharePoint
        if user_id:
            existing_history = load_chat_history_from_sharepoint(user_id, access_token)
            existing_history.append({
                "question": question,
                "answer": answer,
                "document_path": document_url
            })
            
            sp_file_path = f"chat-history/{user_id}.json"
            sp_upload_url = (
                f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}"
                f"/drives/{SHAREPOINT_DRIVE_ID}/root:/{sp_file_path}:/content"
            )
            try:
                upload_response = requests.put(
                    sp_upload_url,
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    data=json.dumps(existing_history, indent=2).encode("utf-8")
                )
                if upload_response.status_code in (200, 201):
                    print(f" Chat history uploaded to SharePoint at: {sp_file_path}")
                else:
                    print(f" Upload failed: {upload_response.status_code} - {upload_response.text}")
            except Exception as e:
                print(f" Upload exception: {e}")

        return jsonify({
            'answer': answer,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'response_time': response_time,
            'document_path': document_url,
            'follow_up_required': follow_up_required,
            'relevant_document_found': relevant_document_found
        })

    except Exception as e:
        print(" Unhandled exception in /query route:", str(e))
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {e}"}), 500


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
            answer, _, _, _, document_path = asyncio.run(query_agent(question, CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID))
            # answer, _, _, _, document_path = query_agent(question, DOCUMENTS_FOLDER)
            document_url = f"http://127.0.0.1:5000/DocPDFIMG/{os.path.basename(document_path)}" if document_path else None
            session["chat_history"].append({"question": question, "answer": answer, "document_path": document_url})
            session.modified = True

    return render_template("index.html", chat_history=session["chat_history"])

# from flask import jsonify

# import asyncio

@app.route('/reload_index', methods=['POST'])
def reload_index():
    """Reloads documents using preconfigured credentials from configure.py."""
    try:
        documents, file_id_map = asyncio.run(load_documents(CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID))
        return jsonify({
            "message": "Documents reloaded successfully",
            "documents_count": len(documents),
            "file_mapping": file_id_map
        }), 200
    except Exception as e:
        print(f"Error reloading documents: {str(e)}")
        return jsonify({"error": f"Failed to reload documents: {str(e)}"}), 500


@app.route('/reload_documents', methods=['POST'])
def reload_documents():
    try:
        asyncio.run(load_or_build_faiss_hnsw_index(
            CLIENT_ID, CLIENT_SECRET, TENANT_ID, SHAREPOINT_SITE_ID,
            force_rebuild=True  # Always force rebuild via this route
        ))
        return jsonify({"message": "FAISS index rebuilt successfully"}), 200
    except Exception as e:
        print(f"Error rebuilding FAISS index: {e}")
        return jsonify({"error": str(e)}), 500

# @app.route('/reload_documents', methods=['GET'])
# def reload_documents():
#     """Reloads documents from the DOCUMENTS_FOLDER."""
#     try:
#         documents = load_documents(DOCUMENTS_FOLDER)
#         return jsonify({"message": "Documents reloaded successfully", "documents_count": len(documents)}), 200
#     except Exception as e:
#         print(f"Error reloading documents: {str(e)}")
#         return jsonify({"error": f"Failed to reload documents: {str(e)}"}), 500
    
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
    if IS_SECURE:
        uvicorn.run(asgi_app, host=APP_HOST, port=APP_PORT, ssl_certfile=SSL_CERTFILE,
        ssl_keyfile=SSL_KEYFILE ),
    else:
        uvicorn.run(asgi_app, host=APP_HOST, port=APP_PORT),