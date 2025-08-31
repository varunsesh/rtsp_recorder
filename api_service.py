#!/usr/bin/python3

from flask import Flask, request, jsonify
import json
import subprocess
import os
import sys

# --- CONFIGURATION ---
CONFIG_FILE = "/home/varun/camera_service/config.json"
RECORDER_SERVICE_NAME = "rtsp-recorder.service"

app = Flask(__name__)

# --- API ENDPOINTS ---

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"})

@app.route('/api/config', methods=['GET'])
def get_config():
    """Reads and returns the current config.json."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        return jsonify(config_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config', methods=['POST'])
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
    # Run on port 5000, accessible from any device on the network (0.0.0.0)
    app.run(host='0.0.0.0', port=5000, debug=True)