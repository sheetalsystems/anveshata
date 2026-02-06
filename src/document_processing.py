# src/document_processing.py
import os
import PyPDF2
from docx import Document
import time
from sentence_transformers import SentenceTransformer
import numpy as np
from pdf2image import convert_from_path
import pytesseract
import concurrent.futures
import google.generativeai as genai
from google.generativeai import GenerativeModel, configure
from src.config import GEN_AI_API_KEY, GENERATIVE_MODEL, EMBEDDING_MODEL
from src.onedrive_integration import get_sharepoint_file_content, get_sharepoint_file_ids
import asyncio
import docx
import requests
import json
import io
import aiohttp
from urllib.parse import quote

# Configure the Gemini API key.
configure(api_key=GEN_AI_API_KEY)  # Replace with your actual API key.
model = GenerativeModel(GENERATIVE_MODEL)
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
cached_documents = {}

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

def chunk_text(text, chunk_size=5000):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

async def load_documents(client_id, client_secret, tenant_id, site_id):
    """Loads .docx documents from SharePoint into memory and chunks them."""
    global cached_documents
    cached_documents = {}

    file_items = await get_sharepoint_file_ids(client_id, client_secret, tenant_id, site_id) #Await the async function.

    if not file_items or not file_items["value"]:
        print("No files found or error retrieving file list.")
        return
    #print(file_items);
    for item in file_items["value"]:
        if "file" in item and item["file"]["mimeType"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            download_url = item["@microsoft.graph.downloadUrl"]
            try:
                response = requests.get(download_url)
                response.raise_for_status()
                content = response.content

                doc = docx.Document(io.BytesIO(content))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

                # Add chunking here
                chunk_size = 5000  # Set your desired chunk size
                chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
                cached_documents[item["name"]] = chunks  # Cache the list of text chunks
                print(f"Loaded and chunked: {item['name']} into {len(chunks)} chunks")

            except requests.exceptions.RequestException as e:
                print(f"Error downloading {item['name']}: {e}")
            except Exception as e:
                print(f"Error processing {item['name']}: {e}")
        else:
            print(f"Skipping non-docx or folder: {item.get('name', 'unknown')}")

async def download_and_process_doc(session, download_url, item_name, cached_documents):
    """Downloads a DOCX file and extracts text content, ignoring images."""
    try:
        async with session.get(download_url, timeout=30) as response:
            response.raise_for_status()
            content = await response.read()
            if content:
                try:
                    doc = docx.Document(io.BytesIO(content))
                    text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                    cached_documents[item_name] = text
                    print(f"Loaded text content from: {item_name}")
                except docx.opc.exceptions.PackageNotFoundError:
                    print(f"Error: Invalid DOCX file - {item_name}")
                except Exception as e:
                    print(f"Error processing DOCX content of {item_name}: {e}")
            else:
                print(f"Warning: Empty content received for {item_name}")
    except aiohttp.ClientError as e:
        print(f"Error downloading {item_name}: {e}")
    except asyncio.TimeoutError:
        print(f"Timeout downloading {item_name}")
    except Exception as e:
        print(f"An unexpected error occurred with {item_name}: {e}")

def get_embedding(text):
    try:
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        print(f"Embedding generation error: {e}")
        return None
    
    

FOLLOW_UP_PHRASES = [
    "tell me more", "explain more", "related to it", "explain in detail", "of it", "more about it", "more about",
    "provide more insights", "provide more details", "provide more information", "elaborate",
    "give detail information about", "give more information about", "give more details about", "give more insights about",
    "give more insights on", "give more details on", "give more information on", "give more insights regarding",
    "give more details regarding", "give more information regarding", "give more insights related to",
    "give more details related to", "give more information related to"
]

def is_follow_up_question(question):
    q = question.lower()
    return any(phrase in q for phrase in FOLLOW_UP_PHRASES)

async def query_agent(question, client_id, client_secret, tenant_id, site_id, chat_history=None):
    global cached_documents
    print("Entering query_agent with question:", question, flush=True)

    if not cached_documents:
        print("cached_documents is empty, attempting to load...", flush=True)
        try:
            await load_documents(client_id, client_secret, tenant_id, site_id)
            print("load_documents completed.", flush=True)
        except Exception as e:
            error_message = f"Error loading documents: {e}"
            print(error_message, flush=True)
            return error_message, 0, 0, 0, None

    if not cached_documents:
        return "No documents found in the folder.", 0, 0, 0, None

    is_follow_up = is_follow_up_question(question)
    context = []
    most_relevant_document = None

    try:
        question_embedding = get_embedding(question)
        if not question_embedding:
            return "Could not generate embedding for the question.", 0, 0, 0, None
    except Exception as e:
        return f"Error getting question embedding: {e}", 0, 0, 0, None

    relevant_docs_with_similarity = []

    for file_id, chunks in cached_documents.items():
        best_chunk = None
        highest_sim = -1
        for chunk in chunks:
            chunk_embedding = get_embedding(chunk)
            if chunk_embedding is not None:
                similarity = np.dot(question_embedding, chunk_embedding)
                if similarity > highest_sim:
                    highest_sim = similarity
                    best_chunk = chunk
        if best_chunk:
            relevant_docs_with_similarity.append({
                "file_id": file_id,
                "chunk": best_chunk,
                "similarity": highest_sim
            })

    # Sort and select top K
    top_k = 5
    top_k_docs = sorted(relevant_docs_with_similarity, key=lambda x: x['similarity'], reverse=True)[:top_k]
    
    if top_k_docs:
        most_relevant_document = top_k_docs[0]["file_id"]
        for doc in top_k_docs:
            context.append(f"Document: {doc['file_id']}\n{doc['chunk']}")
    else:
        context.append("No relevant documents found.")

    # Build prompt
    prompt = ""

    if chat_history:
        for entry in chat_history[-2:]:  # Limit to last 2 exchanges
            prompt += f"User: {entry['question']}\nBot: {entry['answer']}\n---\n"

    if is_follow_up:
        prompt += "\nThis is a follow-up to the previous conversation. Keep the previous context in mind.\n"

    prompt += f"\nGiven the following document excerpts:{''.join(context)}"
    prompt += f"User: {question}\nBot: . Give the answer in bullet points or in numbers. Also provide the name of the most relatable document at the end of the answer."

    print("Prompt preview:", prompt[:500], flush=True)

    answer = "No relevant answer found"
    input_tokens = 0
    output_tokens = 0
    response_time = 0

    try:
        start_time_llm = time.time()
        response_obj = model.generate_content(prompt)
        response_time = time.time() - start_time_llm

        if response_obj and hasattr(response_obj, 'text'):
            answer = response_obj.text.strip()

        if response_obj and hasattr(response_obj, 'usage_metadata'):
            input_tokens = getattr(response_obj.usage_metadata, 'prompt_token_count', 0)
            output_tokens = getattr(response_obj.usage_metadata, 'candidates_token_count', 0)
    except Exception as e:
        answer = f"An error occurred during response generation: {e}"
        print(answer, flush=True)

    print("Exiting query_agent with answer:", answer[:50], "...", flush=True)
    return answer, input_tokens, output_tokens, response_time, most_relevant_document
        
# async def query_agent(question, client_id, client_secret, tenant_id, site_id, chat_history=None):
#     """Queries the AI agent with a question and returns the answer."""
#     global cached_documents
#     print("Entering query_agent with question:", question, flush=True)

#     if not cached_documents:
#         print("cached_documents is empty, attempting to load...", flush=True)
#         try:
#             await load_documents(client_id, client_secret, tenant_id, site_id)
#             print("load_documents completed.", flush=True)
#         except Exception as e:
#             error_message = f"Error loading documents: {e}"
#             print(error_message, flush=True)
#             return error_message, 0, 0, 0, None

#     if not cached_documents:
#         return "No documents found in the folder.", 0, 0, 0, None

#     question_embedding = None
#     try:
#         start_time_embedding_q = time.time()
#         question_embedding = get_embedding(question)
#         end_time_embedding_q = time.time()
#         print(f"Time to get question embedding: {end_time_embedding_q - start_time_embedding_q} seconds", flush=True)
#         if not question_embedding:
#             return "Could not generate embedding for the question.", 0, 0, 0, None
#     except Exception as e:
#         error_message = f"Error getting question embedding: {e}"
#         print(error_message, flush=True)
#         return error_message, 0, 0, 0, None

#     print("Starting context building...", flush=True)
#     start_time_context = time.time()
#     context = []
#     most_relevant_document = None
#     highest_similarity = -1

#     for file_id, chunks in cached_documents.items():
#         print(f"Processing file: {file_id}, Chunks: {len(chunks)}", flush=True)
#         if chunks:
#             similarities = []
#             most_similar_chunk_for_file = None
#             highest_similarity_for_file = -1

#             for i, chunk in enumerate(chunks):
#                 print(f"Processing chunk {i+1}/{len(chunks)} for {file_id}", flush=True)
#                 start_time_embedding_c = time.time()
#                 chunk_embedding = get_embedding(chunk)
#                 end_time_embedding_c = time.time()
#                 print(f"Time to get chunk embedding for '{file_id}', chunk {i+1}: {end_time_embedding_c - start_time_embedding_c} seconds", flush=True)
#                 if chunk_embedding:
#                     similarity = np.dot(question_embedding, chunk_embedding)
#                     similarities.append(similarity)
#                     if similarity > highest_similarity_for_file:
#                         highest_similarity_for_file = similarity
#                         most_similar_chunk_for_file = chunk
#                         if similarity > highest_similarity:
#                             highest_similarity = similarity
#                             most_relevant_document = file_id
#                 else:
#                     similarities.append(-1)

#             if most_similar_chunk_for_file:
#                 context.append(f"Document: {file_id}\n{most_similar_chunk_for_file}")
#         print(f"Finished processing file: {file_id}, Context size: {len(context)}", flush=True)

#     end_time_context = time.time()
#     print(f"Context building took: {end_time_context - start_time_context} seconds", flush=True)

#     prompt = ""
#     if chat_history:  # Add chat history to prompt
#         for entry in chat_history:
#             prompt += f"Question: {entry['question']}Answer: {entry['answer']}"
#     prompt += f"Given the following document excerpts, answer the question:{''.join(context)}Question: {question}Answer: .also provide name of most relatable document at the end of the answer.Also give me the detail answer in bullet point or in numbers"

#     print("Generated prompt:", prompt[:100], "...", flush=True)
#     answer = "No relevant answer found"
#     input_tokens = 0
#     output_tokens = 0
#     response_time = 0
#     try:
#         start_time_llm = time.time()
#         response_obj = model.generate_content(prompt)
#         end_time_llm = time.time()
#         response_time = end_time_llm - start_time_llm
#         print(f"Time for language model response: {response_time} seconds", flush=True)
#         if response_obj and hasattr(response_obj, 'text'):
#             answer = response_obj.text.strip()
#         if response_obj and hasattr(response_obj, 'usage_metadata'):
#             if hasattr(response_obj.usage_metadata, 'prompt_token_count'):
#                 input_tokens = response_obj.usage_metadata.prompt_token_count
#             if hasattr(response_obj.usage_metadata, 'candidates_token_count'):
#                 output_tokens = response_obj.usage_metadata.candidates_token_count
#     except Exception as e:
#         answer = f"An error occurred during response generation: {e}"
#         print(answer, flush=True)

#     print("Exiting query_agent with answer:", answer[:50], "...", flush=True)
#     return answer, input_tokens, output_tokens, response_time, most_relevant_document




# query_agent withoiut top 'k' chunks
# async def query_agent(question, client_id, client_secret, tenant_id, site_id, chatHistory=None):
#     """Queries the AI agent with a question, supports follow-up questions and returns the answer."""
#     global cached_documents
#     print("Entering query_agent with question:", question, flush=True)

#     if not cached_documents:
#         print("cached_documents is empty, attempting to load...", flush=True)
#         try:
#             await load_documents(client_id, client_secret, tenant_id, site_id)
#             print("load_documents completed.", flush=True)
#         except Exception as e:
#             error_message = f"Error loading documents: {e}"
#             print(error_message, flush=True)
#             return error_message, 0, 0, 0, None

#     if not cached_documents:
#         return "No documents found in the folder.", 0, 0, 0, None

#     # Detect follow-up question
#     is_follow_up = False
#     context = []
#     most_relevant_document = None
#     highest_similarity = -1

#     if chatHistory and len(chatHistory) > 0:
#         last_qa = chatHistory[-1]
#         follow_up_phrases = ["tell me more", "explain more", "related to it", "explain in detail", "of it","more about it", "more about","provide more insoghts", "provide more details", "provide more information","elaborate", "give detail information about", "give more information about", "give more details about", "give more insights about", "give more insights on", "give more details on", "give more information on", "give more insights regarding", "give more details regarding", "give more information regarding", "give more insights related to", "give more details related to", "give more information related to"]
#         if any(phrase in question.lower() for phrase in follow_up_phrases):
#             is_follow_up = True
#             context.append(f"Previous User: {last_qa['question']}")
#             context.append(f"Previous Bot: {last_qa['answer']}")
#             print("Follow-up question detected. Added previous Q&A to context.")

#     # Get embedding for the question
#     try:
#         start_time_embedding_q = time.time()
#         question_embedding = get_embedding(question)
#         end_time_embedding_q = time.time()
#         print(f"Time to get question embedding: {end_time_embedding_q - start_time_embedding_q:.2f}s", flush=True)
#         if not question_embedding:
#             return "Could not generate embedding for the question.", 0, 0, 0, None
#     except Exception as e:
#         error_message = f"Error getting question embedding: {e}"
#         print(error_message, flush=True)
#         return error_message, 0, 0, 0, None

#     print("Starting context building...", flush=True)
#     start_time_context = time.time()
#     for file_id, chunks in cached_documents.items():
#         print(f"Processing file: {file_id}, Chunks: {len(chunks)}", flush=True)
#         if chunks:
#             similarities = []
#             best_chunk = None
#             max_sim = -1

#             for i, chunk in enumerate(chunks):
#                 print(f"Processing chunk {i+1}/{len(chunks)} for {file_id}", flush=True)
#                 start_time_embedding_c = time.time()
#                 chunk_embedding = get_embedding(chunk)
#                 end_time_embedding_c = time.time()
#                 print(f"Time to get chunk embedding: {end_time_embedding_c - start_time_embedding_c:.2f}s", flush=True)

#                 if chunk_embedding:
#                     similarity = np.dot(question_embedding, chunk_embedding)
#                     similarities.append(similarity)
#                     if similarity > max_sim:
#                         max_sim = similarity
#                         best_chunk = chunk
#                         if similarity > highest_similarity:
#                             highest_similarity = similarity
#                             most_relevant_document = file_id
#                 else:
#                     similarities.append(-1)

#             if best_chunk:
#                 context.append(f"Document: {file_id}\n{best_chunk}")
#         print(f"Finished processing file: {file_id}, Context size: {len(context)}", flush=True)

#     end_time_context = time.time()
#     print(f"Context building took: {end_time_context - start_time_context:.2f}s", flush=True)

#     # Build the final prompt
#     prompt = ""
#     if chatHistory:
#         recent_entries = chatHistory[-2:]
#         for entry in recent_entries:
#             prompt += f"User: {entry['question']}\nBot: {entry['answer']}\n---\n"
#     prompt += f"Given the following document excerpts, answer the question:\n\n{'\n\n'.join(context)}\n\n"
#     prompt += f"User: {question}\nBot: . Give the answer in bullet points or in numbers. Also provide the name of the most relatable document at the end of the answer."

#     print("Prompt preview:", prompt[:500], flush=True)

#     # Call the language model
#     answer = "No relevant answer found"
#     input_tokens = 0
#     output_tokens = 0
#     response_time = 0
#     try:
#         start_time_llm = time.time()
#         response_obj = model.generate_content(prompt)
#         end_time_llm = time.time()
#         response_time = end_time_llm - start_time_llm
#         print(f"Time for language model response: {response_time:.2f}s", flush=True)
#         if response_obj and hasattr(response_obj, 'text'):
#             answer = response_obj.text.strip()
#         if response_obj and hasattr(response_obj, 'usage_metadata'):
#             if hasattr(response_obj.usage_metadata, 'prompt_token_count'):
#                 input_tokens = response_obj.usage_metadata.prompt_token_count
#             if hasattr(response_obj.usage_metadata, 'candidates_token_count'):
#                 output_tokens = response_obj.usage_metadata.candidates_token_count
#     except Exception as e:
#         answer = f"An error occurred during response generation: {e}"
#         print(answer, flush=True)

#     print("Exiting query_agent with answer:", answer[:50], "...", flush=True)
#     return answer, input_tokens, output_tokens, response_time, most_relevant_document
