# src/config.py
import os
from datetime import timedelta

GEN_AI_API_KEY="AIzaSyANy_vhv3t7Q4qzJ82sDzmvlY7f_Ou5RBo"
GENERATIVE_MODEL="gemini-1.5-flash-002"
EMBEDDING_MODEL="all-mpnet-base-v2"

# Define the folder where your documents are stored.
DOCUMENTS_FOLDER = "DocPDFIMG"

# Define the path to the JSON file containing user credentials.
USERS_JS_PATH = "users.json"

# Define the token expiry time.
TOKEN_EXPIRY = timedelta(days=30)

TOKEN_FILE = "jwt_token.json" 

GRAPH_TOKEN_FILE = "graph_token.json"

#domain name
DOMAIN_NAME = "http://www.nbpoc.com:5000"  # Replace with your actual domain name or IP address

# OneDrive configuration (replace with your values)

#ONEDRIVE_ID = "YOUR_ONEDRIVE_ID"
#LOCAL_DOCUMENTS_FOLDER = "onedrive_files"
SHAREPOINT_SITE_ID="systemsp.sharepoint.com,55651af5-6827-4eb9-84d2-09945a4a5ebb,eec0d96e-d69a-46fe-879f-eea1e016263b" # Replace with your SharePoint site ID

#onedrive app password
