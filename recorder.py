#!/usr/bin/python3

import json
import subprocess
import sys
import os
import time
import socket

# --- SCRIPT START ---

CONFIG_FILE = "./config.json"

# --- NEW FUNCTION: The Pre-flight Check ---
def wait_for_camera(camera_name, host, port, timeout=5, wait_interval=30):
    """
    Waits until a TCP connection can be made to the camera's IP and port.
    Returns True if successful, False if it gives up (it currently never gives up).
    """
    print(f"[{camera_name}] Performing pre-flight check: waiting for {host}:{port} to be online...")
    
    while True:
        try:
            # Set a timeout for the connection attempt
            socket.setdefaulttimeout(timeout)
            # Try to create a connection
            with socket.create_connection((host, port)):
                print(f"[{camera_name}] Success! Camera is online at {host}:{port}.")
                return True
        except (socket.error, socket.timeout) as e:
            print(f"[{camera_name}] Camera not ready at {host}:{port}. Retrying in {wait_interval} seconds... (Error: {e})")
            time.sleep(wait_interval)


def start_ffmpeg_process(camera_name, camera_config, common_options, base_dir):
    """Builds and starts a single ffmpeg process for a given camera."""
    
    # --- PRE-FLIGHT CHECK IS CALLED HERE ---
    # Extract IP and Port for the check
    ip_parts = camera_config['ip_address'].split(':')
    host = ip_parts[0]
    # Default RTSP port is 554 if not specified
    port = int(ip_parts[1]) if len(ip_parts) > 1 else 554
    
    wait_for_camera(camera_name, host, port)
    # --- END OF PRE-FLIGHT CHECK ---
    
    rtsp_url = (
        f"rtsp://{camera_config['username']}:{camera_config['password']}@"
        f"{camera_config['ip_address']}/{camera_config['rtsp_path']}"
    )
    
    output_dir = os.path.join(base_dir, camera_config['folder_name'])
    os.makedirs(output_dir, exist_ok=True)
    
    output_pattern = os.path.join(output_dir, f"{camera_name}-%Y%m%d-%H%M%S.mp4")

    command = [
        "ffmpeg",
        "-rtsp_transport", common_options.get('rtsp_transport', 'tcp'),
        "-timeout", "5000000",
        "-i", rtsp_url,
        "-c:v", "copy",
        #"-b:v", common_options.get('bitrate', '2M'),
        "-map", "0",
        "-f", "segment",
        "-segment_time", common_options.get('segment_time', '10'),
        "-segment_format", "mp4",
        "-reset_timestamps", "1",
        "-strftime", "1",
        output_pattern
    ]
    print(f"[{camera_name}] Command: {' '.join(command)}")
    print(f"[{camera_name}] Starting ffmpeg process...")
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        return process
    except Exception as e:
        print(f"[{camera_name}] ERROR starting ffmpeg: {e}")
        return None

def main():
    """Main function to load config and manage all camera processes."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"FATAL: Could not read or parse config file {CONFIG_FILE}. Error: {e}")
        sys.exit(1)
        
    common_options = config.get("common_ffmpeg_options", {})
    base_dir = config.get("base_output_dir", "/tmp")
    
    processes = {}
    
    for key, camera_conf in config.items():
        if key.startswith("camera_") and camera_conf.get("enabled", False):
            process = start_ffmpeg_process(key, camera_conf, common_options, base_dir)
            if process:
                processes[key] = process
    
    if not processes:
        print("No enabled cameras found in config. Exiting.")
        sys.exit(0)
        
    print("\nAll recording processes started. This script will now monitor them.")

    try:
        while True:
            for name, proc in processes.items():
                if proc.poll() is not None:
                    print(f"\nCRITICAL: Process for {name} has terminated unexpectedly!")
                    if proc.stderr:
                        stderr_output = proc.stderr.read()
                        print(f"FFmpeg error output for {name}:\n{stderr_output}")
                    sys.exit(1)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nShutdown signal received. Terminating all ffmpeg processes...")
        for proc in processes.values():
            proc.terminate()
        for proc in processes.values():
            proc.wait()
        print("All processes stopped. Exiting.")

if __name__ == "__main__":
    main()
