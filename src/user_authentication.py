# src/user_authentication.py
import json
import jwt
from datetime import datetime
from functools import wraps
from flask import request, jsonify, current_app
import os
from src.config import TOKEN_FILE

def get_users_from_json(USERS_JS_PATH):
    """Loads users from the users.json file."""
    try:
        with open(USERS_JS_PATH, "r") as file:
            users = json.load(file)
            return users
    except FileNotFoundError:
        print(f"Error: {USERS_JS_PATH} not found.")
        return []
    except json.JSONDecodeError:
        print(f"Error: {USERS_JS_PATH} is not valid JSON.")
        return []
    except Exception as e:
        print(f"Error loading users from JSON file: {e}")
        return []

def jwt_required(f):
    """Decorator to protect routes with JWT authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            # Decode the token, using current_app.secret_key
            decoded = jwt.decode(token.split("Bearer ")[-1], current_app.secret_key, algorithms=["HS256"])
            request.user = decoded  # Attach the decoded user info to the request
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated_function


def save_token_to_file(token):
    """Save the token to a file."""
    try:
        with open(TOKEN_FILE, "w") as file:
            json.dump({"token": token}, file)
    except Exception as e:
        print(f"Error saving token to file: {e}")

def load_token_from_file():
    """Load the token from the file."""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as file:
                data = json.load(file)
                return data.get("token")
        return None
    except Exception as e:
        print(f"Error loading token from file: {e}")
        return None