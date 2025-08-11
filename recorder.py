#!/usr/bin/python3

import json
import subprocess
import sys
import os
import time
import signal

# --- SCRIPT START ---

# The absolute path to the configuration file
CONFIG_FILE = "./config.json"

def start_ffmpeg_process(camera_name, camera_config, common_options, base_dir):
    """Builds and starts a single ffmpeg process for a given camera."""
    
    # Build the RTSP URL
    rtsp_url = (
        f"rtsp://{camera_config['username']}:{camera_config['password']}@"
        f"{camera_config['ip_address']}/{camera_config['rtsp_path']}"
    )
    
    # Create the specific output directory for this camera
    output_dir = os.path.join(base_dir, camera_config['folder_name'])
    os.makedirs(output_dir, exist_ok=True)
    
    output_pattern = os.path.join(output_dir, f"{camera_name}-%Y%m%d-%H%M%S.mp4")

    # Build the ffmpeg command
    command = [
        "ffmpeg",
        "-rtsp_transport", common_options['rtsp_transport'], # This should already be there
        "-stimeout", "5000000",   # <--- ADD THIS LINE (Timeout in microseconds)
        "-i", rtsp_url,
        "-c:v",
        # "-b:v", common_options['bitrate'],
        "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", common_options['segment_time'],
        "-segment_format", "mp4",
        "-reset_timestamps", "1",
        "-strftime", "1",
        output_pattern
    ]
    
    print(f"Starting process for {camera_name}...")
    print(f"Command: {' '.join(command)}")
    
    # Start the process in the background.
    # stdout=subprocess.DEVNULL and stderr=subprocess.PIPE will keep the main script clean
    # but allow us to capture errors if the process fails immediately.
    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return process
    except FileNotFoundError:
        print(f"ERROR for {camera_name}: ffmpeg command not found.")
        return None
    except Exception as e:
        print(f"ERROR starting ffmpeg for {camera_name}: {e}")
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
    
    # Loop through all items that start with "camera_"
    for key, camera_conf in config.items():
        if key.startswith("camera_") and camera_conf.get("enabled", False):
            process = start_ffmpeg_process(key, camera_conf, common_options, base_dir)
            if process:
                processes[key] = process
                print(f"Started recording for {key} with PID {process.pid}")
    
    if not processes:
        print("No enabled cameras found in config. Exiting.")
        sys.exit(0)
        
    print("\nAll recording processes started. This script will now monitor them.")
    print("Press Ctrl+C to stop all recordings.")

    # This loop keeps the main script alive and checks if any processes have crashed.
    try:
        while True:
            for name, proc in processes.items():
                # poll() returns the exit code if the process has terminated, otherwise None.
                if proc.poll() is not None:
                    print(f"\nCRITICAL: Process for {name} has terminated unexpectedly!")
                    stderr_output = proc.stderr.read().decode()
                    print(f"FFmpeg error output for {name}:\n{stderr_output}")
                    # In a more advanced script, you could try to restart it here.
                    # For now, we exit so systemd can restart the whole script.
                    sys.exit(1)
            time.sleep(10) # Check every 10 seconds
    except KeyboardInterrupt:
        print("\nShutdown signal received. Terminating all ffmpeg processes...")
        for name, proc in processes.items():
            print(f"Stopping process for {name}...")
            proc.terminate() # Send SIGTERM
        
        # Wait for all processes to terminate
        for proc in processes.values():
            proc.wait()
        print("All processes stopped. Exiting.")

if __name__ == "__main__":
    main()