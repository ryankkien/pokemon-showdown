#!/usr/bin/env python3
"""
Convenience script to run the bot with server management.
"""

import subprocess
import time
import sys
import os
import signal
import psutil

def find_process_by_port(port):
    """Find process using a specific port."""
    try:
        # Use lsof command instead of psutil to avoid permission issues
        result = subprocess.run(['lsof', '-i', f':{port}'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and 'LISTEN' in result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if 'LISTEN' in line:
                    return int(line.split()[1])  # PID is second column
    except (subprocess.SubprocessError, ValueError, IndexError):
        pass
    return None

def is_server_running(port=8000):
    """Check if Pokemon Showdown server is running."""
    return find_process_by_port(port) is not None

def start_server():
    """Start the Pokemon Showdown server."""
    print("Starting Pokemon Showdown server...")
    
    # Make scripts executable
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "scripts")
    subprocess.run(["chmod", "+x", os.path.join(scripts_dir, "setup_server.sh"), os.path.join(scripts_dir, "start_server.sh")])
    
    # Start server in background
    server_process = subprocess.Popen(
        [os.path.join(scripts_dir, "start_server.sh")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    for i in range(60):  # Wait up to 60 seconds
        if is_server_running():
            print("\nServer started successfully!")
            return server_process
        time.sleep(1)
        print(".", end="", flush=True)
    
    print("\nFailed to start server!")
    return None

def stop_server():
    """Stop the Pokemon Showdown server."""
    pid = find_process_by_port(8000)
    if pid:
        print(f"Stopping server (PID: {pid})...")
        try:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            # Force kill if still running
            if find_process_by_port(8000):
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

def main():
    """Main function to manage server and run bot."""
    server_process = None
    
    try:
        # Check if server is already running
        if not is_server_running():
            server_process = start_server()
            if not server_process:
                print("Failed to start server. Exiting.")
                sys.exit(1)
            time.sleep(2)  # Give server time to fully initialize
        else:
            print("Server already running on port 8000")
        
        # Run the bot
        print("\nStarting Pokemon Showdown bot...")
        print("-" * 50)
        
        # Import and run the bot
        import asyncio
        from src.bot.bot import main as bot_main
        
        asyncio.run(bot_main())
        
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Only stop server if we started it
        if server_process:
            print("\nStopping server...")
            stop_server()
        else:
            print("\nLeaving server running (it was already running when we started)")

if __name__ == "__main__":
    # Check dependencies
    try:
        import psutil
    except ImportError:
        print("Installing required dependency: psutil")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
        import psutil
    
    main()