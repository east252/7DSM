# ----- Imports -----------------------------------------------------------------------------------
import asyncio
import collections
import json
import os
import psutil
import re
import requests
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import xml.etree.ElementTree as ET
import zipfile

from datetime import datetime
from dotenv import load_dotenv
import zstandard as zstd  # ✅ High-speed compression

# ----- Load Environment Variables ----------------------------------------------------------------

load_dotenv()

# ----- Classes -----------------------------------------------------------------------------------

class ServerAPI:
    """Handles authentication and communication with the 7 Days to Die server API dynamically."""

    def __init__(self, base_url):
        """Initialize with API base URL and authentication details."""
        self.base_url = base_url
        self.token_name = os.getenv("APITOKEN_Name")
        self.token_secret = os.getenv("APITOKEN_Secret")

        if not self.token_name or not self.token_secret:
            raise ValueError("❌ Missing API token credentials in .env file!")

    def request(self, method, endpoint, data=None, params=None):
        """Handles any API request dynamically (GET, POST, etc.)."""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {
            "X-SDTD-API-TOKENNAME": self.token_name,
            "X-SDTD-API-SECRET": self.token_secret,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                return {"status": "error", "message": "Invalid HTTP method"}

            response.raise_for_status()
            return response.json()
        
        except requests.RequestException as e:
            return {"status": "error", "message": f"Request failed: {e}"}

    def get(self, endpoint, params=None):
        """Shortcut for GET requests"""
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint, data=None):
        """Shortcut for POST requests"""
        return self.request("POST", endpoint, data=data)

# ----- Global Variables --------------------------------------------------------------------------

SERVER_APP_ID = "294420"
SERVER_DIR = os.path.abspath("Server")
STEAMCMD_DIR = "steamcmd"
STEAMCMD_EXE = os.path.join(STEAMCMD_DIR, "steamcmd.exe")
STEAMCMD_ZIP_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
STEAMCMD_ZIP_PATH = "steamcmd_temp.zip"
SERVER_CONFIG_PATH = os.path.join(SERVER_DIR, "serverconfig.xml")
SERVERADMIN_PATH = os.path.join("Server", "UserDataFolder", "Saves", "serveradmin.xml")
SERVER_LOG_PATH = os.path.join("Server", "Logs")
SERVER_EXE = "7DaysToDieServer.exe"
DONORBUFFER_ENABLED = os.getenv("DONORBUFFER_Enabled", "false").lower() == "true"
DONORBUFFER_SIZE = int(os.getenv("DONORBUFFER_Size", "0"))
VIP_LIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vip_list.txt")
MAX_PLAYERS = 0
CURRENT_PLAYERS = 0  # ✅ Initialize globally
STEAM_AUTH_DELAY = 2  # ✅ Give Steam 2 seconds to authenticate before kicking

api = ServerAPI(base_url="http://localhost:8080") 
# ----- Functions / Definitions -------------------------------------------------------------------

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
    """Installs the 7 Days to Die server using SteamCMD, with optional experimental version."""
    if not os.path.exists(STEAMCMD_EXE):
        print("❌ SteamCMD is not installed. Please run the install command first.")
        return

    print("🚀 Installing 7 Days to Die server...")

    # ✅ Check if we should install the experimental version
    install_experimental = os.getenv("INSTALLCONFIG_Experimental", "false").lower() == "true"

    # ✅ Build the SteamCMD command
    steamcmd_command = [
        STEAMCMD_EXE, 
        "+force_install_dir", SERVER_DIR, 
        "+login", "anonymous", 
        "+app_update", SERVER_APP_ID, "validate"
    ]

    if install_experimental:
        steamcmd_command.append("-beta latest_experimental")  # ✅ Enable experimental build

    steamcmd_command.append("+exit")  # ✅ Prevents auto-starting the server

    try:
        process = subprocess.Popen(
            steamcmd_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Stream output in real-time
        for line in process.stdout:
            print(line, end='')

        process.wait()
        stderr_output = process.stderr.read().strip()

        if process.returncode != 0 and not any(keyword in stderr_output for keyword in ["Update complete", "Cleaning up", "Installing update"]):
            print(f"❌ Possible error during installation: {stderr_output}. Review the line above.")
        else:
            print("✅ 7 Days to Die installation complete. The server was NOT launched.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


def update():
    """Updates the 7 Days to Die server using SteamCMD, with optional experimental version."""
    if not os.path.exists(STEAMCMD_EXE):
        print("❌ SteamCMD is not installed. Please run the install process first.")
        return

    # ✅ Check if we should install the experimental version
    install_experimental = os.getenv("INSTALLCONFIG_Experimental", "false").lower() == "true"

    # ✅ Build the SteamCMD command
    steamcmd_command = [
        STEAMCMD_EXE, 
        "+force_install_dir", SERVER_DIR, 
        "+login", "anonymous", 
        "+app_update", SERVER_APP_ID, "validate"
    ]

    if install_experimental:
        steamcmd_command.append("-beta latest_experimental")  # ✅ Enable experimental build

    steamcmd_command.append("+exit")  # ✅ Prevents auto-starting the server

    print("🚀 Updating 7 Days to Die server...")

    try:
        process = subprocess.Popen(
            steamcmd_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Stream output in real-time
        for line in process.stdout:
            print(line, end='')

        process.wait()
        stderr_output = process.stderr.read().strip()

        if process.returncode != 0 and "Update complete" not in stderr_output:
            print(f"❌ Error during update:\n{stderr_output}")
        else:
            print("✅ 7 Days to Die update complete.")

    except Exception as e:
        print(f"❌ Error launching SteamCMD: {e}")

async def start():
    """Starts the 7DTD server with settings from global variables."""
    server_config_override()  # ✅ Ensure the config is updated before launch
    update_serveradmin_tokens() # ✅ Ensure the web token is installed before launch.

    executable = os.path.join(SERVER_DIR, SERVER_EXE)  # ✅ Corrected to use global variable

    if not os.path.exists(executable):
        print(f"❌ Error: {executable} not found.")
        return

    logs_dir = os.path.join(SERVER_DIR, "Logs")
    os.makedirs(logs_dir, exist_ok=True)

    config_file = os.path.join(SERVER_DIR, "serverconfig.xml")
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

    print("🔍 Launching monitor_server()...")
    threading.Thread(target=lambda: asyncio.run(monitor_server()), daemon=True).start()  # ✅ Ensures monitoring is always running

    try:
        os.chdir(SERVER_DIR)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True
        )

        print("✅ Server started successfully.")

        # ✅ **CALL THE LOGGING FUNCTION**
        threading.Thread(target=stream_logs_to_files, args=(process, main_log_path, error_log_path), daemon=True).start()

        # ✅ Return to the main menu after starting the server
        await main_menu()

    except Exception as e:
        print(f"❌ Error launching the server: {e}")

def server_config_override():
    """Ensures serverconfig.xml matches the values from .env by updating, adding missing entries, and cleaning up formatting."""

    if not os.path.exists(SERVER_CONFIG_PATH):
        print("❌ serverconfig.xml not found. Cannot override settings.")
        return

    print("🔧 Updating serverconfig.xml...")

    # ✅ Read all .env variables that start with "SERVERCONFIG_"
    server_config_vars = {
        key.replace("SERVERCONFIG_", "").lower(): value
        for key, value in os.environ.items() if key.startswith("SERVERCONFIG_")
    }

    # Load and parse the XML file
    tree = ET.parse(SERVER_CONFIG_PATH)
    root = tree.getroot()

    updated_keys = set()

    # ✅ Step 1: Update existing properties
    for prop in root.findall("property"):
        name = prop.get("name", "").lower()
        if name in server_config_vars:
            prop.set("value", server_config_vars[name])
            updated_keys.add(name)

    # ✅ Step 2: Add missing properties
    for key, value in server_config_vars.items():
        if key not in updated_keys:
            ET.SubElement(root, "property", name=key, value=value)

    # ✅ Step 3: Format the XML properly
    xml_string = ET.tostring(root, encoding="unicode")

    # ✅ Force `</ServerSettings>` onto a new line
    xml_string = re.sub(r"(\s*)</ServerSettings>", r"\n</ServerSettings>", xml_string)

    # ✅ Remove extra blank lines
    xml_string = re.sub(r"\n\s*\n", "\n", xml_string)

    # ✅ Ensure proper indentation for `<property>` entries
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

    # ✅ Save the cleaned-up XML file
    with open(SERVER_CONFIG_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(formatted_lines) + "\n")

    print("✅ serverconfig.xml updated successfully.")

def update_serveradmin_tokens():
    """Ensures serveradmin.xml contains the correct API token settings from .env."""

    if not os.path.exists(SERVERADMIN_PATH):
        print("❌ serveradmin.xml not found. Cannot update API tokens.")
        return

    print("🔧 Updating serveradmin.xml...")

    # ✅ Read all .env variables that start with "APITOKEN_"
    api_token_vars = {
        key.replace("APITOKEN_", "").lower(): value
        for key, value in os.environ.items() if key.startswith("APITOKEN_")
    }

    # Ensure required values exist
    name = api_token_vars.get("name")
    secret = api_token_vars.get("secret")
    permission_level = api_token_vars.get("permission")

    if not all([name, secret, permission_level]):
        print("❌ Missing required APITOKEN values in .env. Skipping update.")
        return

    # Load and parse the XML file
    tree = ET.parse(SERVERADMIN_PATH)
    root = tree.getroot()

    # Find or create the <apitokens> section
    apitokens = root.find("apitokens")
    if apitokens is None:
        apitokens = ET.SubElement(root, "apitokens")

    # ✅ Remove any existing token entries
    for token in apitokens.findall("token"):
        apitokens.remove(token)

    # ✅ Add new token entry
    ET.SubElement(apitokens, "token", name=name, secret=secret, permission_level=permission_level)

    # ✅ Format the XML properly
    xml_string = ET.tostring(root, encoding="unicode")

    # ✅ Ensure proper indentation for `<token>` entries
    formatted_lines = []
    for line in xml_string.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("<token"):
            formatted_lines.append(f"\t{stripped_line}")
        elif stripped_line == "</apitokens>":
            formatted_lines.append("")
            formatted_lines.append("</apitokens>")
        else:
            formatted_lines.append(line)

    # ✅ Save the cleaned-up XML file
    with open(SERVERADMIN_PATH, "w", encoding="utf-8") as file:
        file.write("\n".join(formatted_lines) + "\n")

    print("✅ serveradmin.xml updated successfully.")

async def monitor_server():
    """Continuously checks if the server is running and restarts if it stops."""
    print("🛠️ Server monitoring started...")
    await asyncio.sleep(5)

    while True:
        # ✅ Check if the server process is running
        server_running = any(
            proc.info["name"].lower() == "7daystodieserver.exe"
            for proc in psutil.process_iter(["name"])
        )

        if not server_running:
            print("\n\n❌ Server has stopped! Attempting restart...")
            await asyncio.sleep(5)  # ✅ Short delay before retrying

            # ✅ Double-check if the server is still down before restarting
            server_running = any(
                proc.info["name"].lower() == "7daystodieserver.exe"
                for proc in psutil.process_iter(["name"])
            )

            if not server_running:
                print("🔄 Restarting the server...")
                
                # ✅ Corrected executable path
                executable = os.path.join(SERVER_DIR, SERVER_EXE)

                if not os.path.exists(executable):
                    print(f"❌ Error: {executable} not found. Restart failed.")
                else:
                    threading.Thread(target=lambda: asyncio.run(start()), daemon=True).start()
                    print("✅ Server restart triggered. Returning to menu.")

        await asyncio.sleep(10)  # ✅ Check every 10 seconds (non-blocking)
  # ✅ Check every 10 seconds (non-blocking)

def restart_server():
    """Restarts the server process."""
    print("🔄 Restarting the server...")

    try:
        start()  # ✅ Call `start()` directly (it's now synchronous)
        print("✅ Server restart triggered.")
 
    except Exception as e:
        print(f"\n\n❌ Error restarting the server: {e}")

async def stop():
    """Immediately stops the game server without a graceful shutdown (Version 1)."""

    # Use the global variable SERVER_EXE
    server_exe = SERVER_EXE

    # Check if the server is running
    server_running = any(proc.info["name"] == server_exe for proc in psutil.process_iter(["name"]))

    if not server_running:
        print("⚠ Server is not running.")
        sys.exit()  # ✅ Exit the program if the server is not running

    print("⚠ Initiating immediate server shutdown...")

    # Directly force-terminate the server
    kill_server_process()

    print("✅ Server stopped.")
    sys.exit()  # ✅ Exit the program after stopping the server

def kill_server_process():
    """Finds and forcefully kills the server process."""
    for process in psutil.process_iter(["name"]):
        if process.info["name"] == SERVER_EXE:
            print(f"🚨 Terminating process: {SERVER_EXE}")
            process.terminate()

def backup():
    """Creates a highly compressed backup based on .env settings, allowing subdirectory backups."""
    load_dotenv()  # ✅ Ensure .env is loaded

    print("🔄 Starting backup process...")

    # Record the start time
    start_time = time.time()

    # ✅ Read .env variables for backup configuration
    backup_targets = {
        key.replace("BACKUPCONFIG_", "").lower(): value.lower() == "true"
        for key, value in os.environ.items() if key.startswith("BACKUPCONFIG_")
    }

    # ✅ Define paths
    working_dir = os.getcwd()
    server_dir = os.path.join(working_dir, "Server")  # ✅ Scan inside `Server/`
    
    if not os.path.exists(server_dir):
        print("❌ Server directory not found. Backup cannot proceed.")
        return

    # ✅ Get all top-level items in `Server/` (case-insensitive)
    server_items = {item.lower(): os.path.join(server_dir, item) for item in os.listdir(server_dir)}

    # ✅ List of items to back up
    backup_items = []

    # ✅ Always include .env from working directory
    env_path = os.path.join(working_dir, ".env")
    if os.path.exists(env_path):
        print("✅ Including .env in backup.")
        backup_items.append(env_path)

    # ✅ Check for each required backup item inside `Server/`
    for key, should_backup in backup_targets.items():
        if should_backup:
            # ✅ Handle subdirectories using `_` notation
            key_parts = key.split("_")  # Example: Data_Worlds → ["data", "worlds"]
            matched_path = server_dir

            for part in key_parts:
                matched_path = os.path.join(matched_path, part)

            if os.path.exists(matched_path):
                print(f"✅ Including {matched_path} in backup.")
                backup_items.append(matched_path)
            else:
                print(f"⚠ Skipping {key.replace('_', '/')} : Not found in Server directory.")

    if not backup_items:
        print("❌ No items to back up. Exiting backup process.")
        return

    # ✅ Define backup filename
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"backup_{timestamp}.tar.zst"
    backup_path = os.path.join(working_dir, backup_filename)

    print(f"📦 Creating backup: {backup_filename}")

    try:
        tar_filename = f"backup_{timestamp}.tar"
        tar_path = os.path.join(working_dir, tar_filename)

        # ✅ Create a .tar file
        with tarfile.open(tar_path, "w") as tar:
            for item in backup_items:
                tar.add(item, arcname=os.path.relpath(item, start=working_dir))  # ✅ Preserve folder structure in tar

        # ✅ Compress the .tar file using streaming zstd
        with open(tar_path, "rb") as tar_file, open(backup_path, "wb") as compressed_backup:
            cctx = zstd.ZstdCompressor(level=10)
            with cctx.stream_writer(compressed_backup) as compressor:
                shutil.copyfileobj(tar_file, compressor)  # ✅ Stream-based compression

        # ✅ Cleanup the .tar file after compression
        os.remove(tar_path)

        print(f"✅ Backup completed successfully: {backup_filename}")

    except Exception as e:
        print(f"❌ Error creating backup: {e}")

    # Record the end time
    end_time = time.time()

    # Calculate and print the elapsed time
    elapsed_time = end_time - start_time
    print(f"⏱️ Backup process took {elapsed_time:.2f} seconds.")

def stream_logs_to_files(proc, main_log, error_log):
    """Streams server logs and extracts player-related data in real-time, properly handling errors."""
    global MAX_PLAYERS, CURRENT_PLAYERS

    CONTEXT_SIZE = 20
    prev_lines = collections.deque(maxlen=CONTEXT_SIZE)

    error_regex = re.compile(r'\b(ERR|EXCEPTION|CRITICAL|FATAL|ERROR)\b', re.IGNORECASE)
    shader_regex = re.compile(r'\b(Shader)\b', re.IGNORECASE)  # ✅ Ignore all Shader-related logs
    max_players_regex = re.compile(r"Maximum allowed players: (\d+)")
    player_count_regex = re.compile(r"Ply:\s*(\d+)")
    player_join_regex = re.compile(r"PlayerLogin:\s*(.+)")
    steam_id_regex = re.compile(r"PltfmId='(Steam_\d+)'")
    steam_auth_regex = re.compile(r"\[Steamworks\.NET\] Authenticating player: (.+) SteamId: (\d+)")

    # ✅ Temporary storage for player names before Steam authentication
    pending_auth = {}

    with open(main_log, 'w', encoding='utf-8') as main_f, \
         open(error_log, 'w', encoding='utf-8') as err_f:

        for line in iter(proc.stdout.readline, ''):
            if not line and proc.poll() is not None:
                break

            line_stripped = line.strip()

            # ✅ Ignore Shader warnings/errors
            if shader_regex.search(line_stripped):
                continue

            timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            formatted_line = f"[{timestamp}] {line}"

            # ✅ Write to main log
            main_f.write(formatted_line)
            main_f.flush()
            prev_lines.append(formatted_line)

            # ✅ Extract Max Players
            match_max_players = max_players_regex.search(line_stripped)
            if match_max_players:
                MAX_PLAYERS = int(match_max_players.group(1))
                print(f"🎯 Updated Max Players: {MAX_PLAYERS}")

            # ✅ Extract Current Players
            match_player_count = player_count_regex.search(line_stripped)
            if match_player_count:
                CURRENT_PLAYERS = int(match_player_count.group(1))

            # ✅ Detect Player Join (Store in pending_auth)
            match_login = player_join_regex.search(line_stripped)
            if match_login:
                player_name = match_login.group(1)
                pending_auth[player_name] = None  # ✅ Store name, waiting for Steam ID

            # ✅ Detect Steam ID (Assign to the correct player)
            match_steam = steam_id_regex.search(line_stripped)
            if match_steam:
                steam_id = match_steam.group(1)

                # ✅ Find player name from pending_auth
                for name in list(pending_auth.keys()):
                    if pending_auth[name] is None:
                        pending_auth[name] = steam_id
                        break

            # ✅ Detect Steam authentication log
            match_auth = steam_auth_regex.search(line_stripped)
            if match_auth:
                player_name = match_auth.group(1)
                steam_id = f"Steam_{match_auth.group(2)}"

                # ✅ Now enforce VIP check
                enforce_vip_access(player_name, steam_id)

            # ✅ Write errors to error log (with 20-line buffer)
            if error_regex.search(line_stripped):
                for pline in prev_lines:  # ✅ Write last 20 lines before error
                    err_f.write(pline)
                err_f.write("\n" * 5)  # ✅ Add spacing between errors
                err_f.flush()

def is_vip(steam_id):
    """Checks if a Steam ID is in the VIP list and not expired."""
    if not os.path.exists(VIP_LIST_PATH):
        print(f"❌ ERROR: VIP list not found at {VIP_LIST_PATH}. No one is VIP.")
        return False

    try:
        with open(VIP_LIST_PATH, "r", encoding="utf-8") as vip_file:
            for line in vip_file:
                parts = line.strip().split()
                if len(parts) < 4:
                    continue  

                vip_steam_id, vip_name, vip_exp_date, vip_time = parts
                vip_steam_id = vip_steam_id.strip()
                vip_exp_date = vip_exp_date.strip()
                vip_time = vip_time.strip()

                try:
                    vip_expire_date = datetime.strptime(f"{vip_exp_date} {vip_time}", "%Y-%m-%d %H:%M:%S")
                except ValueError as e:
                    continue

                if vip_steam_id == steam_id:
                    if datetime.now() < vip_expire_date:
                        return True  # ✅ VIP and not expired
                    else:
                        return False  

    except FileNotFoundError:
        return False  

    return False

def enforce_vip_access(player_name, steam_id):
    """Checks if a joining player is VIP and kicks them if they are not."""
    global CURRENT_PLAYERS

    buffer_limit = MAX_PLAYERS - DONORBUFFER_SIZE

    if CURRENT_PLAYERS < buffer_limit:
        return  # ✅ Do nothing if we're not in buffer mode

    if is_vip(steam_id):
        return

    # ✅ Wait for Steam authentication before kicking
    time.sleep(STEAM_AUTH_DELAY)
    api.post("command", {"command": f'kick {steam_id} "Thank you for visiting. We are at max capacity. VIPs only may join at this time."'})

# ----- Functions (Server Manager Logic) -----
def server_api_send():
    """ Allows the user to interact with any API endpoint and returns to the main menu after execution. """
    while True:
        print("\n📡 API Interaction")
        print("===================")
        print("1. Fetch available commands")
        print("2. Send a command to the server")
        print("3. Get a list of game items")
        print("4. Get a list of installed mods")
        print("5. Custom API request")
        print("9. Return to main menu")

        choice = input("Enter your choice: ")

        if choice == "1":
            response = api.get("command")
        elif choice == "2":
            command = input("Enter command: ").strip()
            response = api.post("command", {"command": command})
        elif choice == "3":
            response = api.get("item")
        elif choice == "4":
            response = api.get("mods")
        elif choice == "5":
            endpoint = input("Enter API endpoint (without '/api/'): ").strip()
            method = input("Enter HTTP method (GET/POST): ").strip().upper()
            data = None
            if method == "POST":
                data_input = input("Enter JSON data for POST (or leave blank): ").strip()
                data = {} if not data_input else eval(data_input)  # ⚠ Be careful with eval() in real-world use
            response = api.request(method, endpoint, data=data)
        elif choice == "9":
            return  # ✅ Exit back to the main menu
        else:
            print("❌ Invalid choice. Try again.")
            continue  # Loop again

        # ✅ Pretty-print JSON response
        print("\n➡️ API Response:")
        print(json.dumps(response, indent=4))  # ✅ Formats response with indentation

        input("\nPress Enter to return to the main menu...")  # ✅ Wait for user input before returning
        return  # ✅ Ensures the function exits back to main menuTry again.")
    
# ----- Main --------------------------------------------------------------------------------------
async def main_menu():
    """Displays the main menu and handles user input."""
    while True:
        print("\n7 Days to Die Server Manager")
        print("============================")
        print("Choose an option:")
        print("")
        print("1. Install SteamCMD and Server")
        print("2. Update")
        print("3. Start Server")
        print("4. Backup")
        print("5. Server API")
        print("9. Exit (Kills server if running)")
        choice = input("Enter your choice: ")
        if choice == "1":
            install_steam()
            install_server()
        elif choice == "2":
            update()
        elif choice == "3":
            await start()
        elif choice == "4":
            backup()
        elif choice == "5":
            server_api_send()
        elif choice == "9":
            await stop()
        else:
            print("Invalid choice. Try again.")

def main():
    """Starts the program and displays the menu."""
    asyncio.run(main_menu())  # ✅ Calls main_menu() directly, no loop needed here

# ----- Program  ----------------------------------------------------------------------------------
 
if __name__ == "__main__":
    print("7 Days Server Manager")
    print("Author: Njinir")
    print("Created: 2025")
    print("Primal Rage Gaming")
    print("")
    main()