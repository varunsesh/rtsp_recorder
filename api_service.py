#!/usr/bin/python3
# At the top of api_server.py
from flask import Flask, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests
from functools import wraps
import json
import sys
import subprocess 

# --- CONFIGURATION ---
CONFIG_FILE = "/home/varun/camera_service/config.json"
RECORDER_SERVICE_NAME = "rtsp-recorder.service"


# --- NEW AUTHENTICATION DECORATOR ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check for token in the 'Authorization' header
        if 'Authorization' in request.headers:
            # Header should be "Bearer <idToken>"
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Verify the token with Google's servers
            idinfo = id_token.verify_oauth2_token(token, requests.Request())
            
            # Load allowed users from config
            with open(CONFIG_FILE, 'r') as conf_file:
                config = json.load(conf_file)
            
            # AUTHORIZATION STEP: Check if the user's email is in our list
            if idinfo['email'] not in config.get('allowed_users', []):
                return jsonify({'message': 'User is not authorized!'}), 401

            # Pass the verified user info to the route if needed
            kwargs['current_user'] = idinfo

        except ValueError:
            # Invalid token
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(*args, **kwargs)
    return decorated


app = Flask(__name__)

# --- API ENDPOINTS ---

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"})

@app.route('/api/config', methods=['GET'])
@token_required
def get_config():
    """Reads and returns the current config.json."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        return jsonify(config_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
@token_required
def set_config():
    print("Received request to update config")
    """Receives new JSON data and overwrites the config file."""
    new_config = request.json
    if not new_config:
        return jsonify({"error": "Invalid JSON data provided"}), 400
    
    try:
        # Add basic validation here if needed
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=2)
        return jsonify({"status": "success", "message": "Configuration saved."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recorder/restart', methods=['POST'])
@token_required
def restart_recorder():
    """Restarts the recorder service to apply new settings."""
    try:
        subprocess.run(["sudo", "systemctl", "restart", RECORDER_SERVICE_NAME], check=True)
        return jsonify({"status": "success", "message": f"Service '{RECORDER_SERVICE_NAME}' restarted."})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Failed to restart service. Return code: {e.returncode}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recorder/status', methods=['GET'])
@token_required
def get_recorder_status():
    """Checks if the recorder service is active."""
    try:
        result = subprocess.run(["systemctl", "is-active", RECORDER_SERVICE_NAME], capture_output=True, text=True)
        status = result.stdout.strip()
        return jsonify({"service": RECORDER_SERVICE_NAME, "status": status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if sys.argv[1:] and sys.argv[1] == 'dev':
        CONFIG_FILE = "./config.json"
        app.run(host='0.0.0.0', port=5000, debug=True)
    # Run on port 5000, accessible from any device on the network (0.0.0.0)
       # Define the paths to your certificate and key files
    # It's good practice to use absolute paths
    cert_file = '/home/varun/camera_service/cert.pem'
    key_file = '/home/varun/camera_service/key.pem'
    context = (cert_file, key_file)

    # Run the app with the ssl_context to enable HTTPS
    # Remove debug=True before final deployment
    app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=True)
