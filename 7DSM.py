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
telnet_reader = None
telnet_writer = None

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
SERVERCONFIG_TerminalWindowEnabled="false"
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

    # **Wait 30 seconds before attempting Telnet**
    print("⏳ Starting Server..... Waiting 30 seconds before connecting to Telnet.")
    await asyncio.sleep(30)

    # **Now attempt Telnet connection until successful**
    while True:
        await asyncio.sleep(10)  # Wait before retrying
        if telnet_writer is not None:
            print("✅ Telnet is already connected.")
            break
        print("🔌 Attempting Telnet connection...")
        await telnet_connect()  # Retry Telnet connection until successful

    # **Once Telnet is connected, start background Telnet tasks**
    print("📡 Starting Telnet background services...")
    await start_telnet_services()

async def start_telnet_services():
    """Starts Telnet-related background tasks including test commands."""
    await telnet_connect()
    asyncio.create_task(scheduled_player_data())  # Player data every 30 sec
    asyncio.create_task(scheduled_announcements())  # Announcements every 10 min
    asyncio.create_task(test_telnet_say())  # ✅ Correctly scheduled periodic test



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
    pass

async def stop():
    """Shuts down the server via Telnet, ensuring connection stays alive."""
    global telnet_writer

    print("⚠ Initiating server shutdown via Telnet...")

    # **Debug Logging Before Sending Command**
    print(f"🔍 Debug: telnet_writer before shutdown attempt: {telnet_writer}")

    # **Ensure Telnet is still connected**
    if telnet_writer is None:
        print("⚠ Telnet is not connected. Attempting to reconnect before shutdown...")
        await telnet_connect()

    # **Ensure Telnet Writer is Not Lost**
    print(f"🔍 Debug: telnet_writer after reconnect attempt: {telnet_writer}")

    if telnet_writer is None:
        print("❌ Telnet connection failed. Skipping shutdown command.")
    else:
        print("🟢 Sending shutdown command via Telnet (Attempt 1)...")
        success = await telnet_send_command("shutdown")

        await asyncio.sleep(5)

        if is_server_running() and success:
            print("🟢 Sending shutdown command via Telnet (Attempt 2)...")
            await telnet_send_command("shutdown")

        await asyncio.sleep(5)

    if is_server_running():
        print("⏳ Server still running... waiting 5 more seconds.")
        await asyncio.sleep(5)

    if is_server_running():
        print("❌ Server did not shut down in time. Forcing termination.")
        kill_server_process()

    print("🔚 Exiting program.")
    sys.exit(0)



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

async def attempt_connection():
    """Attempts a single Telnet connection."""
    global telnet_reader, telnet_writer
    try:
        print("🔌 Connecting to Telnet...")
        telnet_reader, telnet_writer = await telnetlib3.open_connection(TELNET_HOST, TELNET_PORT)

        # Read initial login prompt
        login_prompt = await telnet_reader.readuntil("Please enter password:")
        if "Please enter password:" in login_prompt:
            telnet_writer.write(TELNET_PASSWORD + "\n")
            await telnet_writer.drain()

        print("✅ Telnet connected successfully.")
        return True

    except Exception as e:
        print(f"❌ Telnet connection failed: {e}")
        telnet_reader, telnet_writer = None, None
        return False

async def telnet_connect():
    """Ensures a persistent Telnet connection and logs its state."""
    global telnet_reader, telnet_writer

    if telnet_writer is not None:
        print("🔄 Telnet is already connected.")
        return

    while True:
        try:
            print("🔌 Connecting to Telnet...")
            telnet_reader, telnet_writer = await telnetlib3.open_connection(
                host=TELNET_HOST, 
                port=TELNET_PORT
            )

            print(f"🔍 Debug: telnet_writer assigned: {telnet_writer}")

            if telnet_writer is None:
                print("❌ Telnet writer is None immediately after connection. Retrying...")
                await asyncio.sleep(10)
                continue

            # ✅ Immediately send password (avoiding waiting for prompt)
            telnet_writer.write(TELNET_PASSWORD + "\n")
            await telnet_writer.drain()

            # ✅ Read authentication response safely
            try:
                auth_resp = await asyncio.wait_for(telnet_reader.read(1024), timeout=2.0)
                print(f"🔑 Telnet authenticated: {auth_resp.strip()}")
            except asyncio.TimeoutError:
                print("⚠ Warning: No immediate response after sending password. Assuming success.")

            print(f"✅ Telnet connected successfully. Writer State: {telnet_writer}")
            return

        except Exception as e:
            print(f"❌ Telnet connection failed: {e}")
            print("⏳ Waiting 10 seconds before retrying Telnet connection...")
            await asyncio.sleep(10)


async def telnet_send_command(command):
    """Sends a command via Telnet, ensuring the connection remains open."""
    global telnet_reader, telnet_writer

    print(f"📡 Sending Telnet command: {command}")

    if telnet_writer is None or telnet_writer.is_closing():
        print("⚠ Telnet connection lost. Attempting to reconnect...")
        await telnet_connect()

    if telnet_writer is None:
        print("❌ Telnet connection failed. Skipping command.")
        return False

    try:
        print(f"🔍 Debug: Writing to Telnet: {command}")

        telnet_writer.write(command + "\n")
        await telnet_writer.drain()

        # ✅ **Handle cases where no response is received**
        try:
            response = await asyncio.wait_for(telnet_reader.readuntil("\n"), timeout=2.0)
            print(f"✅ Telnet Response: {response.strip()}")
        except asyncio.TimeoutError:
            print("⚠ No response received. Assuming command executed successfully.")

        return True

    except Exception as e:
        print(f"❌ Telnet command failed: {e}")
        return False

async def test_telnet_say():
    """Sends a periodic Telnet command 'say "Hello World"' every 30 seconds, ensuring Telnet remains connected."""
    while True:
        if telnet_writer is None or telnet_writer.is_closing():
            print("⚠ Telnet connection lost. Attempting to reconnect...")
            await telnet_connect()

        print("📡 Testing Telnet with 'say \"Hello World\"'...")
        success = await telnet_send_command('say "Hello World"')
        if success:
            print("✅ Test command sent successfully.")
        else:
            print("❌ Test command failed.")

        await asyncio.sleep(30)  # Wait 30 seconds before the next test

async def telnet_disconnect():
    """Closes the Telnet session properly."""
    global telnet_reader, telnet_writer

    if telnet_writer is not None:
        print("🔌 Closing Telnet connection...")
        telnet_writer.close()
        await telnet_writer.wait_closed()
        telnet_reader, telnet_writer = None, None
        print("✅ Telnet disconnected.")

async def scheduled_player_data():
    """Periodically pulls player data via Telnet."""
    while True:
        await asyncio.sleep(30)  # Run every 30 seconds
        response = await telnet_send_command("lp")  # Example: "lp" lists players
        if response:
            print(f"📡 Player Data: {response}")  # Later, we’ll process it better

async def scheduled_announcements():
    """Sends rotating messages to players via Telnet."""
    message_index = 0
    while True:
        await asyncio.sleep(600)  # Run every 10 minutes
        message = announcement_messages[message_index]
        await telnet_send_command(f"say {message}")  # "say" broadcasts to players
        print(f"📢 Announcement sent: {message}")

        message_index = (message_index + 1) % len(announcement_messages)  # Rotate messages



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
            asyncio.run(test_telnet_say())
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