from flask import Flask, jsonify, render_template, request, session, send_file
import os,io
import PyPDF2  # For PDF processing
from docx import Document  # For Word processing
from google.generativeai import GenerativeModel, configure
import secrets
import concurrent.futures
from flask_cors import CORS
import numpy as np
import google.generativeai as genai
from pdf2image import convert_from_path
import pytesseract
import time
from sentence_transformers import SentenceTransformer
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import letter 
from reportlab.lib.utils import simpleSplit
import google.api_core.exceptions
from functools import wraps
from flask import send_from_directory
import jwt
from datetime import datetime, timedelta
import subprocess
import json



#print(genai.__version__)

app = Flask(__name__)
CORS(app)
# CORS(app, origins=["http://localhost:8000", "http://127.0.0.1:5000"])

app.secret_key = secrets.token_hex(16)

USERS_JS_PATH = "users.json"

TOKEN_EXPIRY = timedelta(days=7)


configure(api_key="AIzaSyANy_vhv3t7Q4qzJ82sDzmvlY7f_Ou5RBo")  # Replace with your API key

model = GenerativeModel('gemini-1.5-flash-002')
#embedding_model = genai.GenerativeModel('embedding-001')
embedding_model = SentenceTransformer('all-mpnet-base-v2') 
#print(embedding_model)
#print(hasattr(embedding_model, 'generate_embeddings'))

#try:
#    response = embedding_model.generate_embeddings(contents=[text])
#    print("Embeddings:", response.embeddings[0].values)
#    print("Embedding generation successful!")
#except Exception as e:
#    print(f"Error during embedding generation: {e}")

DOCUMENTS_FOLDER = "DocPDFIMG"
cached_documents = {}
cached_embeddings = {}

app.config['UPLOAD_FOLDER'] = DOCUMENTS_FOLDER
app.add_url_rule('/DocPDFIMG/<path:filename>', 'documents', build_only=True)

def read_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
                try:
                    images = convert_from_path(file_path, first_page=page.page_number + 1, last_page=page.page_number + 1)
                    if images:
                        for img in images:
                            text += pytesseract.image_to_string(img)
                except:
                    pass
            return text
    except Exception as e:
        return f"Error reading PDF file: {e}"

def read_word(file_path):
    try:
        doc = Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except Exception as e:
        return f"Error reading Word file: {e}"

def chunk_text(text, chunk_size=300):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

def load_documents():
    global cached_documents
    #print("Loading documents from folder: {DOCUMENTS_FOLDER}") 
    if cached_documents:
        return cached_documents
    
    #print(f"Loading documents from folder: {DOCUMENTS_FOLDER}") #debugging line.

    if not os.path.exists(DOCUMENTS_FOLDER):
        #print(f"Folder not found: {DOCUMENTS_FOLDER}") #debugging line.
        return {}

    documents = {}
    files = [f for f in os.listdir(DOCUMENTS_FOLDER) if f.lower().endswith((".pdf", ".docx"))]

    #print(f"Found files: {files}") #debugging line.

    def process(filename):
        file_path = os.path.join(DOCUMENTS_FOLDER, filename)
        if filename.lower().endswith(".pdf"):
            return filename, read_pdf(file_path)
        elif filename.lower().endswith(".docx"):
            return filename, read_word(file_path)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = executor.map(process, files)

    for result in results:
        if result:
            filename, content = result
            documents[filename] = chunk_text(content)

    cached_documents = documents
    return cached_documents

# Load documents when the Flask app starts
load_documents()

def get_embedding(text):
    try:
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        print(f"Embedding generation error: {e}")
        return None

def query_agent(question):
    if not cached_documents:
        return "No documents found in the folder.", 0, 0, 0, None

    question_embedding = get_embedding(question)
    if not question_embedding:
        return "Could not generate embedding for the question.", 0, 0, 0, None

    context = []
    most_relevant_document = None
    highest_similarity = -1  # Track the highest similarity score

    for filename, chunks in cached_documents.items():
        if chunks:
            similarities = []
            for chunk in chunks:
                chunk_embedding = get_embedding(chunk)
                if chunk_embedding:
                    similarity = np.dot(question_embedding, chunk_embedding)
                    similarities.append(similarity)
                    # Update the most relevant document if this similarity is the highest
                    if similarity > highest_similarity:
                        highest_similarity = similarity
                        most_relevant_document = os.path.join(DOCUMENTS_FOLDER, filename)
                else:
                    similarities.append(-1)

            if similarities:
                most_similar_index = np.argmax(similarities)
                most_similar_chunk = chunks[most_similar_index]
                context.append(f"Document: {filename}\n{most_similar_chunk}")

    # prompt = f"Given the following document excerpts, answer the question in a well-formatted manner with read more functionality in each answer. show only first 2 lines with read more. do not send another prompt for read more it should be script.Ensure the response includes:Proper HTML formatting without too many space,  left align, Bullet points if applicable to improve readability, At the end of the response, include the most relatable document name and page number in bold.   :\n\n{'\n\n'.join(context)}\n\nQuestion: {question}\n\nAnswer:"
    prompt = f"Given the following document excerpts, answer the question:\n\n{'\n\n'.join(context)}\n\nQuestion: {question}\n\nAnswer: .also provide name of most relatable document at the end of the answer."

    try:
        start_time = time.time()
        response = model.generate_content(prompt)
        end_time = time.time()
        response_time = end_time - start_time
        answer = response.text.strip() if response and response.text else "No relevant answer found"

        input_tokens = 0  # Default value
        output_tokens = 0  # Default value

        # Debugging logs
        print(f"Response.prompt_feedback: {response.prompt_feedback}")
        print(f"Response.usage_metadata: {response.usage_metadata}")

        if response.usage_metadata:
            output_tokens = response.usage_metadata.candidates_token_count if hasattr(response.usage_metadata, 'candidates_token_count') else 0

        if response.usage_metadata and hasattr(response.usage_metadata, 'prompt_token_count'):
            input_tokens = response.usage_metadata.prompt_token_count

        return answer, input_tokens, output_tokens, response_time, most_relevant_document

    except Exception as e:
        return f"An error occurred: {e}", 0, 0, 0, None


def get_users_from_json():
    """Loads users from the users.json file."""
    try:
        
        with open(USERS_JS_PATH, "r") as file:
            users = json.load(file)  # Load JSON data as a Python list
            return users
    except Exception as e:
        print("Error loading users from JSON file:", str(e))
        return []
    
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data or "username" not in data or "password" not in data:
            return jsonify({"error": "Username and password are required"}), 400

        username, password = data["username"], data["password"]
        users = get_users_from_json()  # Fetch users from the JSON file

        # Validate user credentials
        valid_user = any(user for user in users if user["username"] == username and user["password"] == password)

        if not valid_user:
            return jsonify({"error": "Invalid username or password"}), 401

        # Generate JWT token
        token = jwt.encode(
            {"username": username, "exp": datetime.utcnow() + TOKEN_EXPIRY},
            app.secret_key,
            algorithm="HS256"
        )

        return jsonify({"token": token}), 200

    except Exception as e:
        print(f"Error during login: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500
    
def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            # Decode the token
            decoded = jwt.decode(token.split("Bearer ")[-1], app.secret_key, algorithms=["HS256"])
            request.user = decoded  # Attach the decoded user info to the request
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated_function
    
    
@app.route('/DocPDFIMG/<path:filename>')
def documents(filename):
    """
    Serve files from the DocPDFIMG folder.
    """
    return send_from_directory(DOCUMENTS_FOLDER, filename)


@app.route('/chat', methods=['POST'])
@jwt_required
def chat():
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Invalid request, 'question' key missing"}), 400

        question = data["question"]
        answer, input_tokens, output_tokens, response_time, document_path = query_agent(question)
        
        # Handle errors from query_agent
        if isinstance(answer, str) and answer.startswith("An error occurred:") or isinstance(answer, str) and answer.startswith("Could not generate embedding for the question.") or isinstance(answer, str) and answer.startswith("No documents found in the folder."):
            return jsonify({"error": answer}), 500

        # Generate a clickable link for the document path
        document_url = f"http://127.0.0.1:5000/DocPDFIMG/{os.path.basename(document_path)}" if document_path else None

        # Store the question and answer in the session
        chat_history = session.get("chat_history", [])
        chat_history.append({'question': question, 'answer': answer, 'document_path': document_url})
        session['chat_history'] = chat_history  # Save chat history in session

        # Return the response
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

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"message": "Flask app is running"})
    

def simpleSplit(text, font, size, max_width):
    """
    Splits a string into multiple lines based on the width of the text.
    """
    lines = []
    words = text.split(" ")
    current_line = ""

    for word in words:
        # Temporarily add word to current line and check if it fits
        test_line = f"{current_line} {word}".strip()
        if font and size and len(test_line) * size < max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)
    return lines

@app.route('/download_pdf', methods=['GET'])
@jwt_required
def download_pdf():
    # Get chat history from session (you can populate this from your actual chat data)
    chat_history = session.get("chat_history", [])
    print(f"Chat History: {chat_history}")
    
    
    # Prepare a BytesIO buffer to store the PDF data
    buffer = io.BytesIO()
    
    # Create the PDF canvas and define the page size
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # A4 paper size
    left_margin = 50
    right_margin = 50
    bottom_margin = 50
    max_width = width - (left_margin + right_margin)
    y = height - 80  # Start position for text
    page_number = 1
    first_page = True

    # Add header function for the first page
    def add_header():
        """Adds header only on the first page."""
        pdf.setFont("Helvetica-Bold", 14)
        title = "Document-Based Q&A"
        pdf.drawString((width - pdf.stringWidth(title, "Helvetica-Bold", 14)) / 2, height - 50, title)

    # Add footer for page number
    def add_footer():
        """Adds page number footer on each page."""
        pdf.setFont("Helvetica", 10)
        pdf.drawString(width / 2 - 20, bottom_margin / 2, f"Page {page_number}")

    # Add header to first page
    add_header()
    pdf.setFont("Helvetica", 12)

    # Loop through each chat entry and add it to the PDF
    for entry in chat_history:
#         print(f"Chat History: {chat_history}")
        
        # Print the chat history to check if it's being fetched correctly
        print(f"Chat Entry: {entry}")

        if y < bottom_margin + 40:  # If near the bottom, create a new page
            add_footer()
            pdf.showPage()
            page_number += 1
            pdf.setFont("Helvetica", 12)
            y = height - 80  # Reset y position

            if first_page:
                add_header()
                first_page = False

        # Add the question to the PDF
        question_lines = simpleSplit(f"Q: {entry['question']}", "Helvetica", 12, max_width)
        for line in question_lines:
            if y < bottom_margin + 40:  # New page if needed
                add_footer()
                pdf.showPage()
                page_number += 1
                pdf.setFont("Helvetica", 12)
                y = height - 80

            pdf.drawString(left_margin, y, line)
            y -= 20  # Line spacing

        # Add the answer to the PDF
        answer_lines = simpleSplit(f"A: {entry['answer']}", "Helvetica", 12, max_width)
        for line in answer_lines:
            if y < bottom_margin + 40:  # New page if needed
                add_footer()
                pdf.showPage()
                page_number += 1
                pdf.setFont("Helvetica", 12)
                y = height - 80

            pdf.drawString(left_margin + 20, y, line)  # Indent answers slightly
            y -= 20  # Adjust spacing

        y -= 20  # Extra space between Q&A

    # Add footer to the last page
    add_footer()

    # Finalize the PDF
    pdf.save()
    
    # Seek to the beginning of the buffer
    buffer.seek(0)

    # Send the PDF file to the client as an attachment
    return send_file(buffer, as_attachment=True, download_name="AI_agent.pdf", mimetype="application/pdf")

@app.route("/", methods=["GET", "POST"])
def index():
    session.setdefault("chat_history", [])

    if request.method == "POST":
        question = request.form.get("question")
        if question:
            answer = query_agent(question) #uses cache documents
            session["chat_history"].append({"question": question, "answer": answer})
            session.modified = True  # Ensure session updates are saved

    return render_template("index.html", chat_history=session["chat_history"])

@app.route('/reload_documents', methods=['GET'])
def reload_documents():
    """
    Endpoint to reload documents by calling the load_documents() method.
    """
    try:
        documents = load_documents()
        return jsonify({"message": "Documents reloaded successfully", "documents_count": len(documents)}), 200
    except Exception as e:
        print(f"Error reloading documents: {str(e)}")
        return jsonify({"error": f"Failed to reload documents: {str(e)}"}), 500
    

@app.route('/list_documents', methods=['GET'])
def list_documents():
    """
    Endpoint to list all documents in the Documents folder with clickable links.
    """
    try:
        if not os.path.exists(DOCUMENTS_FOLDER):
            return jsonify({"error": "Documents folder not found"}), 404

        files = [f for f in os.listdir(DOCUMENTS_FOLDER) if f.lower().endswith((".pdf", ".docx"))]
        if not files:
            return jsonify({"message": "No documents found in the folder"}), 200

        # Generate clickable links for each document
        document_links = [
            {
                "filename": file,
                "url": f"http://127.0.0.1:5000/static/{file}"
            }
            for file in files
        ]

        return jsonify({"documents": document_links}), 200

    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(debug=True)