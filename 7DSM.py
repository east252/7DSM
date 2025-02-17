# ----- Introduction  -----------------------------------------------------------------------------
# 7 Days Server Manager
# Author: Njinir
# Created: 2025
# Primal Rage Gaming

# This is a Python script for a 7 Days to Die server manager. 
# It uses the 7 Days to Die server API to manage the server. 
# It can start, stop, restart, and update the server. 
# It can also send commands to the server and get the server status.

# ----- Prerequistes -------------------------------------------------------------------------------
""" TODO: Prerequisites:
1. Install python from microsoft store. 3.12 preferably.  
2. Install Visual C++ Redistributable "https://aka.ms/vs/17/release/vc_redist.x64.exe"  
3. Place the program (7DSM.py) in a folder (this is your working folder).
4. When steamcmd and server are installed, they will sit beside this folder.
5. Install the prerequisites using python.
"""

""" Python Prerequisites:
via consle: pip install certifi, chardet, idna, psutil, python-dotenv, requests, telnetlib3, urllib3

Then, fill out the global variables below, if they need changing.
"""

# ----- Libraries ------------------------------------------------------------------------------------
import asyncio
import collections
import os
import psutil
import re
import requests
import shutil
import subprocess
import sys
import threading
import telnetlib3
import time
import xml.etree.ElementTree as ET
import zipfile


# ----- Global Variables -----------------------------------------------------------------------------

    # Telnet Variables
TELNET_HOST="127.0.0.1"
TELNET_PORT = 8081  # Remove quotes to make it an integer
TELNET_PASSWORD="MySecretPassword123"

    # Server Config Variables
SERVERCONFIG_LandClaimCount="5"
SERVERCONFIG_LootAbundance="200"
SERVERCONFIG_GameDifficulty="3"
SERVERCONFIG_ServerName="Njinir"
SERVERCONFIG_ServerPassword="MySecretPassword123"
SERVERCONFIG_ServerMaxPlayerCount="10"
SERVERCONFIG_TelnetEnabled="true"
SERVERCONFIG_TelnetPort="8081"
SERVERCONFIG_TelnetPassword="MySecretPassword123"
SERVERCONFIG_WebDashboardEnabled="true"
SERVERCONFIG_TerminalWindowEnabled="true"
SERVERCONFIG_UserDataFolder="./UserDataFolder"

    # Donor Buffer Settings
DONORBUFFER_ENABLED="true"
DONORBUFFER_SLOTS="10"

    # Server Messages
announcement_messages = [
    "Welcome to the server!",
    "Need help? Check out our Discord.",
    "Don't forget to claim your land!",
]

    # Server Settings


    # Server Manager Commands
SM_Donorlist = "donorlist"
SM_DonorBuffer = "donorbuffer"
SM_SetDonorBuffer = "setdonorbuffer"


    # Global Variables for code
SERVER_APP_ID = "294420"
SERVER_DIR = os.path.abspath("Server")
STEAMCMD_DIR = "steamcmd"
STEAMCMD_EXE = os.path.join(STEAMCMD_DIR, "steamcmd.exe")
STEAMCMD_ZIP_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
STEAMCMD_ZIP_PATH = "steamcmd_temp.zip"
SERVER_CONFIG_PATH = os.path.join(SERVER_DIR, "serverconfig.xml")
SERVER_LOG_PATH = os.path.join("Server", "Logs")  # Path to logs to monitor Telnet readiness
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

# Fix this to work with the new Telnet system.
async def start():
    """Starts the server first, then waits 30 seconds before attempting Telnet connection."""

    # Ensure serverconfig.xml is up to date
    server_config_override()

    server_path = os.path.abspath("Server")
    executable = os.path.join(server_path, SERVER_EXE)

    if not os.path.exists(executable):
        executable = os.path.join(server_path, "7DaysToDie.exe")
        if not os.path.exists(executable):
            print("❌ Error: Neither 7DaysToDieServer.exe nor 7DaysToDie.exe found.")
            return

    logs_dir = os.path.join(server_path, "Logs")
    os.makedirs(logs_dir, exist_ok=True)

    config_file = os.path.join(server_path, "serverconfig.xml")
    if not os.path.exists(config_file):
        print(f"❌ Error: serverconfig.xml not found in {server_path}.")
        return

    # Prepare logs
    log_timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    main_log_path = os.path.join(logs_dir, f"log_{log_timestamp}.txt")
    error_log_path = os.path.join(logs_dir, f"error_{log_timestamp}.txt")

    print(f"🚀 Starting server, main logs -> {main_log_path}")
    print(f"⚠ Error logs -> {error_log_path}")

    # Start the server process **before** connecting to Telnet
    command = [
        executable,
        "-quit", "-batchmode", "-nographics",
        "-configfile=serverconfig.xml",
        "-dedicated"
    ]

    try:
        os.chdir(server_path)  # Ensure correct working directory
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True
        )

        # Start log streaming in a separate thread
        threading.Thread(
            target=stream_logs_to_files,
            args=(process, main_log_path, error_log_path),
            daemon=True
        ).start()

        # Start monitoring thread
        threading.Thread(target=monitor_server, args=(process,), daemon=True).start()

        print("✅ Server started successfully. Logs are being captured.")

    except Exception as e:
        print(f"❌ Error launching the server: {e}")
        return

    # TODO: Add telnet connection after server is running.

def server_config_override():
    """Overrides serverconfig.xml settings with global SERVERCONFIG_ variables."""
    
    # Ensure the config file exists
    if not os.path.exists(SERVER_CONFIG_PATH):
        print("❌ serverconfig.xml not found. Cannot override settings.")
        return
    
    print("🔧 Updating serverconfig.xml...")

    # Get all global variables that start with SERVERCONFIG_
    server_config_vars = {
        key.replace("SERVERCONFIG_", "").lower(): value
        for key, value in globals().items() if key.startswith("SERVERCONFIG_")
    }

    # Load and parse the XML file
    tree = ET.parse(SERVER_CONFIG_PATH)
    root = tree.getroot()

    # Track which keys were updated
    updated_keys = set()

    # Process existing <property> entries
    for prop in root.findall("property"):
        name = prop.get("name", "").lower()
        if name in server_config_vars:
            prop.set("value", server_config_vars[name])  # Update value
            updated_keys.add(name)

    # Add missing properties at the end
    for key, value in server_config_vars.items():
        if key not in updated_keys:
            ET.SubElement(root, "property", name=key, value=value)

    # Convert tree back to a formatted XML string
    xml_string = ET.tostring(root, encoding="unicode")

    # **FORCE** `</ServerSettings>` onto a new line
    xml_string = re.sub(r"(\s*)</ServerSettings>", r"\n</ServerSettings>", xml_string)

    # **FORCE** proper indentation for `<property>` entries
    formatted_lines = []
    for line in xml_string.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("<property"):
            formatted_lines.append(f"\t{stripped_line}")  # Indent properties
        elif stripped_line == "</ServerSettings>":
            formatted_lines.append("")  # Add an empty line before closing tag
            formatted_lines.append("</ServerSettings>")  # Ensure no indentation
        else:
            formatted_lines.append(line)

    # Write the cleaned-up XML file
    with open(SERVER_CONFIG_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(formatted_lines) + "\n")

    print("✅ serverconfig.xml has been updated with correct indentation.")

def join():
    # TODO: Join a current server via Telnet.
    pass

def stop():
    """Stop the server gracefully."""
    if is_server_running():
        print("🟢 Server is running.")
        kill_server_process()
        print("🔴 Server is not running.")
        sys.exit()
    else:
        print("🔴 Server is not running.")
        sys.exit()

def is_server_running():
    """Checks if the server executable is still running."""
    for process in psutil.process_iter(["name"]):
        if process.info["name"] == SERVER_EXE:
            return True
    return False

def kill_server_process():
    """Finds and forcefully kills the server process."""
    for process in psutil.process_iter(["name"]):
        if process.info["name"] == SERVER_EXE:
            print(f"🚨 Terminating process: {SERVER_EXE}")
            process.terminate()


def restart():
    pass

def monitor_server(proc):
    """Monitors the server process and detects crashes."""
    while True:
        if proc.poll() is not None:
            print("❌ Server process terminated unexpectedly.")
            break
        time.sleep(5)

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

def server_logging():
    pass

def vip_list_load():
    pass

# TODO: Fix this function to work with the new Telnet system.
async def telnet_connect():
    """Connects to the Telnet server and logs in."""
    pass

# TODO: Fix this to work with the new Telnet system.
async def telnet_send_command(command):
    """Sends a command via Telnet, ensuring the connection remains open."""
    pass

# TODO: Fix this function to work with the new Telnet system.     
async def telnet_disconnect():
    """Closes the Telnet session properly."""
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
        print("4. Join Telnet (Server must already be running)")
        print("9. Exit (Kills server if running)")
        choice = input("Enter your choice: ")
        if choice == "1":
            install_steam()
            install_server()
        elif choice == "2":
            update()
        elif choice == "3":
            asyncio.run(start())
        elif choice == "4":
            join()
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


""" Goals and Versioning
7DSM

Version 0.0.0.1
- [✅] virtual environment
- [✅] gitignore the steamcmd and server files
- [✅] install server beside, not in, the steamcmd folder
- [✅] allow install of prerequisites from SM menu.
- [✅] enforce telnet true, port, pass from .env file
- [✅] allow update of the server, include validate
- [✅] allow overwrite serverconfig.xml from .env
- [✅] log stamp and flow all logs from server to file
- [✅] ignore or remove WARNING: Shader and ERROR: Shader lines
- [✅] Exit menu which kills the running server instance
- [✅] Send commands to telnet
- [✅] properly display response from telnet into SM
- [✅] Graceful shutdown of server initiated from SM
- [✅] Restart if game crashes
- [✅] Separate error log. 20 lines, 5x separated, if WRN,ERR, Exception

Version 0.0.0.2
- [] Rebuild from the ground up to incorporate the telnet control.
- [✅] virtual environment
- [✅] gitignore the steamcmd and server files
- [✅] install server beside, not in, the steamcmd folder
- [⛔] allow install of prerequisites from SM menu. - Removed Task
- [✅] enforce telnet true, port, pass from .env file
- [✅] allow update of the server, include validate
- [✅] allow overwrite serverconfig.xml from .env !! Changed to from global variables !!
- [✅] log stamp and flow all logs from server to file
- [✅] ignore or remove WARNING: Shader and ERROR: Shader lines
- [] Exit menu which kills the running server instance
- [] Send commands to telnet
- [] properly display response from telnet into SM
- [] Graceful shutdown of server initiated from SM
- [] Restart if game crashes
- [] Separate error log. 20 lines, 5x separated, if WRN,ERR, Exception
- [] Donor buffer has to be created
- [] See if webmap exists already before rewriting
- [] Command to print out all expired claims for admins to hunt down
- [] Donor slot system/vip system
- [] Reset Region Functionality
- [] Server Messages
- [] Save and backup systems
- [] Change C++ redist from menu to auto install


Version 0.0.0.3
- [] Staff or Hard teleports (ftw/type)
- [] Discord Integration
- [] Ping ban

Version 0.0.0.4
- [] Player teleports


To Do List:
Reset Regions
Webmap
Expired landclaim view
Discord integration
Giveplus
Reset Level
Reset Skills
Zombie spawner for admins
Server messages
Chat colors
Vehice Retrieval
"""