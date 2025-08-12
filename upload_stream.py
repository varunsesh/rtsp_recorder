#!/usr/bin/python3
import os
import subprocess
from datetime import datetime
import json
import sys

# --- SCRIPT CONFIGURATION ---

# The absolute path to the one and only configuration file
CONFIG_FILE = "/home/varun/camera_service/config.json"

# --- END OF CONFIGURATION ---


def log_message(log_file_path, message):
    """Prints a message and appends it to the specified log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(log_entry.strip()) # Also print to console for manual runs
    try:
        with open(log_file_path, "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"FATAL: Could not write to log file {log_file_path}. Error: {e}")


def main():
    """The main function to load config and run the upload process."""
    
    # Load configuration from the JSON file
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except Exception as e:
        # If we can't even read the config, we can't log properly. Print and exit.
        print(f"FATAL: Could not read or parse config file {CONFIG_FILE}. Error: {e}")
        sys.exit(1)

    # Get all settings from the loaded config
    source_dir = config.get("base_output_dir")
    log_file = config.get("log_file")
    remote_dest_dir = config.get("upload_dir")
    remote_name = config.get("drive") # Assuming this is constant, or add it to config too.

    # --- Start logging ---
    log_message(log_file, "--- Upload script started. ---")

    # Validate that we got all required settings from the config file
    if not all([source_dir, log_file, remote_dest_dir]):
        log_message(log_file, "ERROR: One or more required keys (base_output_dir, log_file, upload_dir) are missing from config.json. Aborting.")
        log_message(log_file, "--- Upload script finished with error. ---\n")
        return

    # Check if the source directory exists to prevent rclone errors
    if not os.path.isdir(source_dir):
        log_message(log_file, f"ERROR: Source directory not found at '{source_dir}'. Aborting.")
        log_message(log_file, "--- Upload script finished with error. ---\n")
        return

    # Construct the full rclone command using variables from the config
    command = [
        "/usr/bin/rclone",
        "move",
        source_dir,
        f"{remote_name}:{remote_dest_dir}",
        "--include", "*.mp4",      # Only move .mp4 files
        "--delete-empty-src-dirs", # Clean up camera_1_videos etc. when empty
        "--log-level", "INFO"      # Get useful output from rclone
    ]
    
    try:
        # Run the rclone command using subprocess
        log_message(log_file, f"Executing command: {' '.join(command)}")
        
        result = subprocess.run(
            command, 
            check=True,
            capture_output=True,
            text=True
        )
        
        log_message(log_file, "Rclone command completed successfully.")
        if result.stdout:
            log_message(log_file, "Rclone output:\n" + result.stdout)

    except subprocess.CalledProcessError as e:
        log_message(log_file, "!!! RCLONE FAILED with a non-zero exit code !!!")
        log_message(log_file, f"Return Code: {e.returncode}")
        log_message(log_file, "Rclone stdout (if any):\n" + e.stdout)
        log_message(log_file, "Rclone stderr:\n" + e.stderr)
        
    except FileNotFoundError:
        log_message(log_file, "!!! SCRIPT FAILED: 'rclone' command not found at /usr/bin/rclone. Is it installed?")
        
    except Exception as e:
        log_message(log_file, f"An unexpected Python error occurred: {e}")

    log_message(log_file, "--- Upload script finished. ---\n")


if __name__ == "__main__":
    main()
