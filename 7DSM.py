# ----- Introduction  -----------------------------------------------------------------------------
# 7 Days Server Manager 
# Version: 0.0.1
# Author: Njinir
# Created: 2025
# Primal Rage Gaming

# This is a Python script for a 7 Days to Die server manager. 
# It uses the 7 Days to Die server API to manage the server. 
# It can start, stop, restart, and update the server. 

# ----- Prerequistes -------------------------------------------------------------------------------
""" TODO: Prerequisites:
1. Install python from microsoft store. 3.12 preferably.  
2. Install Visual C++ Redistributable "https://aka.ms/vs/17/release/vc_redist.x64.exe"  
3. Place the program (7DSM.py) in a folder (this is your working folder).
4. When steamcmd and server are installed, they will sit beside this folder.
5. Install the prerequisites using python.
6. Create a .env file in the working folder. (This is for your variables/settings)
    NOTE: The .env file is customizable. Add any variables you want to change.
7. Use python's pip to install the prerequisites: python -m pip install -r requirements.txt

Example .env file:

# Server Config Variables (overwrites serverconfig.xml. Add any others as needed.)
SERVERCONFIG_LandClaimCount="5"
SERVERCONFIG_LootAbundance="200"
SERVERCONFIG_GameDifficulty="3"
SERVERCONFIG_ServerName="Njinir"
SERVERCONFIG_ServerPassword="MySecretPassword123"
SERVERCONFIG_ServerMaxPlayerCount="10"
SERVERCONFIG_WebDashboardEnabled="true"
SERVERCONFIG_TerminalWindowEnabled="true"
SERVERCONFIG_UserDataFolder="./UserDataFolder"
"""

# ----- Libraries ------------------------------------------------------------------------------------
import asyncio
import collections
import os
import psutil
import re
import requests
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from dotenv import load_dotenv


# ----- Global Variables -----------------------------------------------------------------------------
SERVER_APP_ID = "294420"
SERVER_DIR = os.path.abspath("Server")
STEAMCMD_DIR = "steamcmd"
STEAMCMD_EXE = os.path.join(STEAMCMD_DIR, "steamcmd.exe")
STEAMCMD_ZIP_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
STEAMCMD_ZIP_PATH = "steamcmd_temp.zip"
SERVER_CONFIG_PATH = os.path.join(SERVER_DIR, "serverconfig.xml")
SERVER_LOG_PATH = os.path.join("Server", "Logs")
SERVER_EXE = "7DaysToDieServer.exe"

# ----- Functions / Definitions -----------------------------------------------------------------------------

def install_steam():
    """Downloads and extracts SteamCMD if not already installed."""
    if os.path.exists(STEAMCMD_EXE):
        print("✔ SteamCMD is already installed. Skipping installation.")
        return

    print("⬇ Downloading SteamCMD...")
    try:
        response = requests.get(STEAMCMD_ZIP_URL, stream=True)
        response.raise_for_status()
        with open(STEAMCMD_ZIP_PATH, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print("✔ Download complete.")
    except requests.RequestException as e:
        print(f"❌ Download failed: {e}")
        return

    print("📦 Extracting SteamCMD...")
    try:
        with zipfile.ZipFile(STEAMCMD_ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(STEAMCMD_DIR)
        os.remove(STEAMCMD_ZIP_PATH)
        print("✔ Extraction complete.")
    except zipfile.BadZipFile as e:
        print(f"❌ Extraction failed: {e}")
        return

def install_server():
    """Installs the 7 Days to Die server using SteamCMD."""
    if not os.path.exists(STEAMCMD_EXE):
        print("❌ SteamCMD is not installed. Please run the install command first.")
        return

    print("🚀 Installing 7 Days to Die server...")

    try:
        process = subprocess.Popen(
            [
                STEAMCMD_EXE, 
                "+force_install_dir", SERVER_DIR, 
                "+login", "anonymous", 
                "+app_update", SERVER_APP_ID, 
                "+quit"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Stream output in real-time
        for line in process.stdout:
            print(line, end='')

        process.wait()

        stderr_output = process.stderr.read().strip()

        # Only show an error if installation actually failed
        if process.returncode != 0 and "Update complete" not in stderr_output:
            print(f"❌ Error during installation: {stderr_output}")
        else:
            print("✅ 7 Days to Die installation complete.")

        # If launch fails, provide an explanation instead of an error message
        if "Update complete, launching..." in stderr_output:
            print("⚠ Skipping launch: Server configuration is not set up yet.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")

    print("Returning to main menu.")

def update():
    """Updates the 7 Days to Die server using SteamCMD."""
    if not os.path.exists(STEAMCMD_EXE):
        print("❌ SteamCMD is not installed. Please run the install process first.")
        return

    # Confirmation prompt
    choice = input("⚠ Are you sure you want to update the server? This may take time. (Y/N): ").strip().lower()
    if choice != "y":
        print("❌ Update canceled.")
        return

    print("🚀 Updating 7 Days to Die server...")

    try:
        process = subprocess.Popen(
            [
                STEAMCMD_EXE, 
                "+force_install_dir", SERVER_DIR, 
                "+login", "anonymous", 
                "+app_update", SERVER_APP_ID, "validate", 
                "+quit"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Stream output in real-time
        for line in process.stdout:
            print(line, end='')

        process.wait()

        stderr_output = process.stderr.read().strip()

        # Only show an error if the update actually failed
        if process.returncode != 0 and "Update complete" not in stderr_output:
            print(f"❌ Error during update:\n{stderr_output}")
        else:
            print("✅ 7 Days to Die update complete.")

    except Exception as e:
        print(f"❌ Error launching SteamCMD: {e}")
    
    print("Returning to main menu.")


async def start():
    """Starts the 7DTD server with settings loaded from .env."""
    server_config_override()  # ✅ Ensure the config is updated before launch

    server_path = os.path.abspath("Server")
    executable = os.path.join(server_path, os.getenv("SERVER_EXE", "7DaysToDieServer.exe"))

    if not os.path.exists(executable):
        print(f"❌ Error: {executable} not found.")
        return

    logs_dir = os.path.join(server_path, "Logs")
    os.makedirs(logs_dir, exist_ok=True)

    config_file = os.path.join(server_path, "serverconfig.xml")
    if not os.path.exists(config_file):
        print("❌ Error: serverconfig.xml not found.")
        return

    log_timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    main_log_path = os.path.join(logs_dir, f"log_{log_timestamp}.txt")
    error_log_path = os.path.join(logs_dir, f"error_{log_timestamp}.txt")

    print(f"🚀 Starting server, logs -> {main_log_path}")

    command = [
        executable,
        "-quit", "-batchmode", "-nographics",
        "-configfile=serverconfig.xml",
        "-dedicated"
    ]

    try:
        os.chdir(server_path)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True
        )

        print("✅ Server started successfully.")

    except Exception as e:
        print(f"❌ Error launching the server: {e}")


def server_config_override():
    """Overrides serverconfig.xml settings with values from .env."""

    if not os.path.exists(SERVER_CONFIG_PATH):
        print("❌ serverconfig.xml not found. Cannot override settings.")
        return

    print("🔧 Updating serverconfig.xml...")

    # Read all .env variables that start with "SERVERCONFIG_"
    server_config_vars = {
        key.replace("SERVERCONFIG_", "").lower(): value
        for key, value in os.environ.items() if key.startswith("SERVERCONFIG_")
    }

    # Load and parse the XML file
    tree = ET.parse(SERVER_CONFIG_PATH)
    root = tree.getroot()

    updated_keys = set()

    # Update existing properties
    for prop in root.findall("property"):
        name = prop.get("name", "").lower()
        if name in server_config_vars:
            prop.set("value", server_config_vars[name])
            updated_keys.add(name)

    # Add missing properties
    for key, value in server_config_vars.items():
        if key not in updated_keys:
            ET.SubElement(root, "property", name=key, value=value)

    # Convert tree to formatted XML
    xml_string = ET.tostring(root, encoding="unicode")

    # Force `</ServerSettings>` to a new line
    xml_string = re.sub(r"(\s*)</ServerSettings>", r"\n</ServerSettings>", xml_string)

    # Properly indent `<property>` entries
    formatted_lines = []
    for line in xml_string.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("<property"):
            formatted_lines.append(f"\t{stripped_line}")
        elif stripped_line == "</ServerSettings>":
            formatted_lines.append("")
            formatted_lines.append("</ServerSettings>")
        else:
            formatted_lines.append(line)

    with open(SERVER_CONFIG_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(formatted_lines) + "\n")

    print("✅ serverconfig.xml updated successfully.")

async def monitor_server():
    """Continuously checks if the server is running and restarts if it stops."""
    server_exe = os.getenv("SERVER_EXE", "7DaysToDieServer.exe")
    server_path = os.path.abspath("Server")
    executable = os.path.join(server_path, server_exe)

    while True:
        # Check if the server process is running
        server_running = any(proc.info["name"] == server_exe for proc in psutil.process_iter(["name"]))

        if not server_running:
            print("❌ Server process not found. Restarting server...")
            await start()  # ✅ Restart the server

        time.sleep(10)  # ✅ Check every 10 seconds

async def stop():
    """Stops the game server gracefully if possible, otherwise forces termination."""
    server_exe = os.getenv("SERVER_EXE", "7DaysToDieServer.exe")

    # Step 1: Check if the server is running
    server_running = any(proc.info["name"] == server_exe for proc in psutil.process_iter(["name"]))

    if not server_running:
        print("⚠ Server is not running.")
        return

    print("⚠ Initiating server shutdown...")

    # Step 2: Attempt a graceful shutdown
    try:
        await send_shutdown_command()  # ✅ Implement this to send a shutdown command via Web API
        print("⏳ Waiting 10 seconds for the server to shut down...")
        time.sleep(10)
    except Exception as e:
        print(f"❌ Error attempting graceful shutdown: {e}")

    # Step 3: Check if the server is still running
    server_running = any(proc.info["name"] == server_exe for proc in psutil.process_iter(["name"]))

    if server_running:
        print("❌ Server did not shut down. Forcing termination...")
        kill_server_process()

    print("✅ Server stopped.")
    sys.exit(0)


def kill_server_process():
    """Finds and forcefully kills the server process."""
    for process in psutil.process_iter(["name"]):
        if process.info["name"] == SERVER_EXE:
            print(f"🚨 Terminating process: {SERVER_EXE}")
            process.terminate()


def restart():
    pass

def server_backup():
    pass

def stream_logs_to_files(proc, main_log, error_log):
    """Streams server logs to separate main and error log files."""
    CONTEXT_SIZE = 20
    prev_lines = collections.deque(maxlen=CONTEXT_SIZE)
    
    # Improved regex to exclude less critical warnings
    error_regex = re.compile(r'\b(ERR|EXCEPTION|CRITICAL|FATAL|ERROR)\b', re.IGNORECASE)
    
    # Track the last error to prevent duplicates
    last_error_message = None

    with open(main_log, 'w', encoding='utf-8') as main_f, \
         open(error_log, 'w', encoding='utf-8') as err_f:

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break

            line_stripped = line.strip()

            # Ignore shader warnings/errors
            if line_stripped.startswith("WARNING: Shader") or line_stripped.startswith("ERROR: Shader"):
                continue

            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            out_line = f"[{timestamp}] {line}"

            main_f.write(out_line)
            main_f.flush()
            prev_lines.append(out_line)

            # Detect critical errors & prevent duplicate consecutive errors
            if error_regex.search(line_stripped):
                if line_stripped != last_error_message:
                    last_error_message = line_stripped  # Update last error message
                    for pline in prev_lines:
                        err_f.write(pline)
                    err_f.write("\n" * 5)  # Add spacing between errors
                    err_f.flush()

def send_shutdown_command():
    """Sends a shutdown command to the server via Web API."""
    pass

# ----- Main -----------------------------------------------------------------------------
def main():
    while True:
        print("7 Days to Die Server Manager")
        print("============================")
        print("Choose an option:")
        print("")
        print("1. Install SteamCMD and Server")
        print("2. Update")
        print("3. Start Server")
        print("9. Exit (Kills server if running)")
        choice = input("Enter your choice: ")
        if choice == "1":
            install_steam()
            install_server()
        elif choice == "2":
            update()
        elif choice == "3":
            asyncio.run(start())
        elif choice == "9":
            stop()
        else:
            print("Invalid choice. Try again.")

# Program
if __name__ == "__main__":
    print("7 Days Server Manager")
    print("Author: Njinir")
    print("Created: 2025")
    print("Primal Rage Gaming")
    print("")
    main()