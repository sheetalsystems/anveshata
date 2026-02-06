
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load all environment variables from .env file
load_dotenv(dotenv_path='.env')


GEN_AI_API_KEY = os.getenv("GEN_AI_API_KEY")
GENERATIVE_MODEL = os.getenv("GENERATIVE_MODEL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY")  # Secret key for Flask app

DOCUMENTS_FOLDER = os.getenv("DocPDFIMG")  # Folder for storing uploaded documents
USERS_JS_PATH = os.getenv("USERS_JS_PATH")    # Path to JSON file with user data

# Tokens
TOKEN_EXPIRY = timedelta(days=30)
TOKEN_FILE = os.getenv("TOKEN_FILE")
GRAPH_TOKEN_FILE =os.getenv("GRAPH_TOKEN_FILE") 

# Domain
DOMAIN_NAME = os.getenv("DOMAIN_NAME")  # Your server/domain for callbacks

# OneDrive Auth Settings
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")

SHAREPOINT_SITE_ID = os.getenv("SHAREPOINT_SITE_ID")
SHAREPOINT_DRIVE_ID = os.getenv("SHAREPOINT_DRIVE_ID")  # SharePoint drive ID for OneDrive

# OneDrive App Credentials (if using different from above)
ONED_NAME = os.getenv("ONED_NAME")
ONED_PASSWORD = os.getenv("ONED_PASSWORD")
ONED_APP_NAME = os.getenv("ONED_APP_NAME")
ONED_CLIENT_ID = os.getenv("ONED_CLIENT_ID")
ONED_TENENT_ID = os.getenv("ONED_TENENT_ID")
ONED_CLIENT_SECRET = os.getenv("ONED_CLIENT_SECRET")
ONED_FOLDER_PATH_URL = os.getenv("ONED_FOLDER_PATH_URL")
ONED_GRAPH_API_URL = os.getenv("ONED_GRAPH_API_URL")
ONED_DOCUMENT_URL = os.getenv("ONED_DOCUMENT_URL")  # URL to access documents in OneDrive
ONED_SHAREPOINT_SITE_ID = os.getenv("ONED_SHAREPOINT_SITE_ID")
ONED_DOCUMENT_URL_QUERY = os.getenv("ONED_DOCUMENT_URL_QUERY" )

APP_PORT = int(os.getenv("APP_PORT"))  # Default port for the app
APP_HOST = os.getenv("APP_HOST")  # Default IP for the app
SSL_KEYFILE = os.getenv('SSL_KEYFILE')
SSL_CERTFILE = os.getenv('SSL_CERTFILE')
IS_SECURE = os.getenv('IS_SECURE', 'no').lower() == 'yes'  # Converts to boolean
CROS_ORIGINS = os.getenv('CROS_ORIGINS', '*')  # CORS origins, default to allow all


AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_URI = os.getenv("REDIRECT_URI") 
# SCOPE = ["User.Read"]
# SCOPE = [
#     "User.Read",
#     "Files.Read.All",
#     "Sites.Read.All"
# ]

SCOPE = [
    "User.Read",
    "Files.ReadWrite.All",
    "Sites.ReadWrite.All"
]
