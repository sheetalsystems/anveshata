import asyncio
import requests
from azure.identity import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from src.config import CLIENT_ID, CLIENT_SECRET, TENANT_ID, GRAPH_TOKEN_FILE
import json
import os

async def get_sharepoint_file_content(client_id, client_secret, tenant_id, site_id, file_id):
    """Retrieves the content of a specific file from SharePoint in memory."""

    scopes = ["Sites.Selected"]  # Or more specific scopes
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

    try:
        api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{file_id}/content"
        #access_token = credential.get_token("https://graph.microsoft.com/.default").token
        # access_token = GRAPH_ACCESS_TOKEN
        access_token = load_graphtoken_from_file()
        if not access_token:
            return jsonify({"error": "Graph token missing or invalid."}), 401
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.content  # Return the file content as bytes
    except Exception as e:
        print(f"Error retrieving SharePoint file content: {e}")
        return None

async def get_sharepoint_file_ids(client_id, client_secret, tenant_id, site_id):
    """Retrieves a list of file IDs from a SharePoint site."""

    scopes = ["Sites.Selected"]  # Or more specific scopes
    credential = ClientSecretCredential(tenant_id, client_id, client_secret)
    graph_client = GraphServiceClient(credentials=credential, scopes=scopes)

#https://graph.microsoft.com/v1.0/sites/systemsp.sharepoint.com,55651af5-6827-4eb9-84d2-09945a4a5ebb,eec0d96e-d69a-46fe-879f-eea1e016263b/drive/root:/NBDocPOC/DocPDFIMG?csf=1&web=1&e=0A0lFB/children
    try:
        api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/NBDocPOC/DocPDFIMG:/children"
        #access_token = credential.get_token("https://graph.microsoft.com/.default").token
        # access_token = GRAPH_ACCESS_TOKEN
        access_token = load_graphtoken_from_file()
        if not access_token:
            return jsonify({"error": "Graph token missing or invalid."}), 401
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        items = json.loads(response.text)
        #print(items)
        return items
        #if items and items.get("value"):
         #   file_ids = [item.get("id") for item in items["value"] if item.get("file")]
            #print(" files found in the specified SharePoint site. get sharepoint file id.")
          #  return file_ids
        #else:
         #   print("No files found in the specified SharePoint site. get sharepoint file id.")
          #  return []
    except Exception as e:
        print(f"Error accessing SharePoint site: {e}")
        return []

async def download_sharepoint_files(client_id, client_secret, tenant_id, site_id, local_folder):
    """Downloads all files from a SharePoint site to a local folder."""
    file_ids = await get_sharepoint_file_ids(client_id, client_secret, tenant_id, site_id)
    if not file_ids:
        return

    for file_id in file_ids:
        file_content = await get_sharepoint_file_content(client_id, client_secret, tenant_id, site_id, file_id)
        if file_content:
            try:
                # Get file name
                scopes = ["Sites.Selected"]
                credential = ClientSecretCredential(tenant_id, client_id, client_secret)
                graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
                api_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/items/{file_id}"
                #access_token = credential.get_token("https://graph.microsoft.com/.default").token
                # access_token = GRAPH_ACCESS_TOKEN
                access_token = load_graphtoken_from_file()
                if not access_token:
                    return jsonify({"error": "Graph token missing or invalid."}), 401
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(api_url, headers=headers)
                response.raise_for_status()
                file_info = json.loads(response.text)
                file_name = file_info.get("name", f"file_{file_id}")

                file_path = os.path.join(local_folder, file_name)
                with open(file_path, "wb") as f:
                    f.write(file_content)
                print(f"Downloaded: {file_name}")
            except Exception as e:
                print(f"Error downloading file {file_id}: {e}")
                

def load_graphtoken_from_file():
    """
    Loads the Microsoft Graph access token from the configured JSON file.
    """
    try:
        if os.path.exists(GRAPH_TOKEN_FILE):
            with open(GRAPH_TOKEN_FILE, "r") as file:
                data = json.load(file)
                return data.get("graph_token")
        else:
            print(f"Token file '{GRAPH_TOKEN_FILE}' not found.")
            return None
    except Exception as e:
        print(f"Error loading Graph token from file: {e}")
        return None