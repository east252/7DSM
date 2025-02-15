import os
import zipfile
import requests
import subprocess
import shutil
import time
import threading
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import telnetlib3
import asyncio
import psutil
import collections
import re  # For matching error/warning lines
import queue  # For event queue

# Load environment variables from .env file
load_dotenv()

TELNET_PORT = int(os.getenv("TELNET_PORT"))
TELNET_PASSWORD = os.getenv("TELNET_PASSWORD").strip()

# Donor Buffer Settings from .env
# (These values come from your .env file if set.)
MAX_PLAYERS = int(os.getenv("SERVERCONFIG_ServerMaxPlayerCount", "50").strip())
DONORBUFFER_ENABLED = os.getenv("DONORBUFFER_ENABLED", "false").strip().lower() in ["true", "1", "yes"]
DONORBUFFER_SLOTS = int(os.getenv("DONORBUFFER_SLOTS", "10").strip())

# Global counter for current players
current_player_count = 0

# --- VIP List Loader ---
def load_vip_list(vip_file="vip_list.txt"):
    """
    Loads VIP players from a file.
    Each line should be: SteamID Name ExpirationDate
    Returns a set of VIP SteamIDs.
    """
    vip_set = set()
    try:
        with open(vip_file, "r") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    vip_set.add(parts[0])
    except Exception as e:
        print(f"Error loading VIP list: {e}")
    return vip_set

# --- Event Bus Integration ---
event_queue = queue.Queue()

def event_dispatcher():
    """
    Continuously dispatch events from the event_queue.
    Handles 'player_join' and 'player_leave' events.
    """
    global current_player_count
    while True:
        event = event_queue.get()
        event_type = event.get("type")
        if event_type == "player_join":
            handle_player_join(event)
        elif event_type == "player_leave":
            handle_player_leave(event)
        else:
            print("Event dispatched:", event)
        event_queue.task_done()

dispatcher_thread = threading.Thread(target=event_dispatcher, daemon=True)
dispatcher_thread.start()

def handle_player_join(event):
    """
    Handles a player join event.
    Expects event to have 'player' and 'steam_id'.
    Increments the player count and, if donor buffer is active,
    kicks non-VIP players if server is nearly full.
    """
    global current_player_count
    player = event.get("player")
    steam_id = event.get("steam_id")
    current_player_count += 1
    print(f"Player join detected: {player} (current count: {current_player_count})")

    if DONORBUFFER_ENABLED and current_player_count >= (MAX_PLAYERS - DONORBUFFER_SLOTS):
        vip_list = load_vip_list()
        # Check if player is VIP by comparing Steam ID.
        if steam_id not in vip_list:
            print(f"Kicking {player} (Steam ID: {steam_id}) - donor buffer active.")
            send_telnet_command(f"kick {player} Donor Buffer active: VIPs only")
        else:
            print(f"{player} (Steam ID: {steam_id}) is VIP. Allowed to join.")
    else:
        print(f"{player} is allowed to join.")

def handle_player_leave(event):
    """
    Handles a player leave event.
    Expects event to have 'player'.
    Decrements the player count.
    """
    global current_player_count
    player = event.get("player")
    current_player_count = max(0, current_player_count - 1)
    print(f"Player leave detected: {player} (current count: {current_player_count})")

# --- Telnet Command Function ---
def send_telnet_command(command):
    """
    Sends a Telnet command to the server.
    For now, it prints the command.
    Later, integrate with your Telnet connection service.
    """
    print(f"Sending Telnet command: {command}")

# --- Existing Functions (Install, Update, etc.) ---

def apply_env_overrides(config_file):
    """
    Applies .env keys like SERVERCONFIG_LootAbundance=200 to serverconfig.xml.
    """
    tree = ET.parse(config_file)
    root = tree.getroot()
    for key, raw_value in os.environ.items():
        if key.startswith("SERVERCONFIG_"):
            env_config_name = key[len("SERVERCONFIG_"):].lower()
            value = raw_value.strip()
            matched = False
            for prop in root.findall('property'):
                if prop.get('name').lower() == env_config_name:
                    old_val = prop.get('value')
                    prop.set('value', value)
                    print(f"Updated {prop.get('name')} from '{old_val}' to '{value}'")
                    matched = True
                    break
            if not matched:
                print(f"WARNING: No property found for env var '{key}' => looking for name='{env_config_name}' in serverconfig.xml")
    tree.write(config_file)
    print(f"Done applying .env overrides to {config_file}.")

def install_cpp_redistributable():
    url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    installer_path = "vc_redist.x64.exe"
    print("Downloading C++ Redistributable...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(installer_path, 'wb') as file:
            file.write(response.content)
        print("Download complete.")
    except requests.RequestException as e:
        print(f"Download failed: {e}")
        return
    print("Installing C++ Redistributable...")
    try:
        subprocess.run([installer_path, '/install', '/quiet', '/norestart'], check=True)
        print("Installation complete.")
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        return
    os.remove(installer_path)
    print("Installer file removed.")

def update():
    steamcmd_dir = "steamcmd"
    steamcmd_path = os.path.join(steamcmd_dir, "steamcmd.exe")
    if not os.path.exists(steamcmd_path):
        print("steamcmd is not installed. Please run the install process first.")
        return
    print("Launching steamcmd to update 7 Days to Die...")
    install_dir = os.path.abspath(os.path.join(os.path.dirname(steamcmd_path), '..', 'Server'))
    try:
        process = subprocess.Popen(
            [steamcmd_path, '+force_install_dir', install_dir, '+login', 'anonymous', '+app_update', '294420', 'validate', '+quit'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            print(line, end='')
        process.wait()
        if process.returncode != 0:
            print(f"Error during update: {process.stderr.read()}")
        else:
            print("7 Days to Die update complete.")
    except Exception as e:
        print(f"Error launching steamcmd: {e}")
        return
    print("Returning to main menu.")

def install():
    steamcmd_dir = "steamcmd"
    steamcmd_path = os.path.join(steamcmd_dir, "steamcmd.exe")
    if os.path.exists(steamcmd_path):
        print("steamcmd is already installed. Skipping download and extraction.")
        launch_and_install(steamcmd_path)
        return
    url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
    zip_path = "steamcmd.zip"
    print("Downloading steamcmd.zip...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(zip_path, 'wb') as file:
            file.write(response.content)
        print("Download complete.")
    except requests.RequestException as e:
        print(f"Download failed: {e}")
        return
    print("Extracting steamcmd...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(steamcmd_dir)
        os.remove(zip_path)
        print("Extraction complete.")
    except zipfile.BadZipFile as e:
        print(f"Error extracting the zip file: {e}")
        return
    launch_and_install(steamcmd_path)

def launch_and_install(steamcmd_path):
    if not os.path.exists(steamcmd_path):
        print("steamcmd.exe not found.")
        return
    print("Launching steamcmd and installing 7 Days to Die...")
    install_dir = os.path.abspath(os.path.join(os.path.dirname(steamcmd_path), '..', 'Server'))
    try:
        process = subprocess.Popen(
            [steamcmd_path, '+force_install_dir', install_dir, '+login', 'anonymous', '+app_update', '294420', '+quit'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        for line in process.stdout:
            print(line, end='')
        process.wait()
        if process.returncode != 0:
            print(f"Error during installation: {process.stderr.read()}")
        else:
            print("7 Days to Die installation complete.")
    except Exception as e:
        print(f"Error launching steamcmd: {e}")
        return
    print("Returning to main menu.")

def start():
    """
    Starts the 7DTD server WITHOUT '-logfile', so logs go to stdout.
    We capture them in 2 logs:
      1) A main log with everything except 'Shader' spam lines.
      2) An error log that includes the last 20 lines plus the error line whenever
         we detect 'ERR', 'WRN', 'Exception', 'Error', or 'Warning' (case-insensitive).
    Additionally, we parse join and disconnect events from logs and publish events.
    """
    # Apply .env overrides to serverconfig.xml
    apply_env_overrides("server/serverconfig.xml")
    server_path = os.path.abspath("Server")
    executable = os.path.join(server_path, "7DaysToDieServer.exe")
    if not os.path.exists(executable):
        executable = os.path.join(server_path, "7DaysToDie.exe")
        if not os.path.exists(executable):
            print("Error: Neither 7DaysToDieServer.exe nor 7DaysToDie.exe found.")
            return
    logs_dir = os.path.join(server_path, "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    config_file = os.path.join(server_path, "serverconfig.xml")
    if not os.path.exists(config_file):
        print(f"Error: serverconfig.xml not found in {server_path}.")
        return
    # Enable Telnet with correct port/password
    tree = ET.parse(config_file)
    root = tree.getroot()
    for prop in root.findall('property'):
        if prop.get('name') == 'TelnetEnabled':
            prop.set('value', 'true')
        elif prop.get('name') == 'TelnetPort':
            prop.set('value', str(TELNET_PORT))
        elif prop.get('name') == 'TelnetPassword':
            prop.set('value', TELNET_PASSWORD)
    tree.write(config_file)

    def monitor_server(process):
        """ If server stops, automatically restart. """
        while True:
            if process.poll() is not None:
                print("Server process terminated. Restarting...")
                asyncio.run(start_server_task())
                break
            time.sleep(5)

    def stream_logs_to_files(proc, main_log_path, error_log_path):
        """
        Main log: writes all lines (timestamped) EXCEPT lines starting with
                  "WARNING: Shader" or "ERROR: Shader".
        Error log: whenever a line matches (ERR|WRN|EXCEPTION|ERROR|WARNING),
                   we dump the previous 20 lines plus the current line, then
                   add 5 blank lines.
        Also, we check for join/disconnect events and publish them.
        """
        CONTEXT_SIZE = 20
        prev_lines = collections.deque(maxlen=CONTEXT_SIZE)
        error_regex = re.compile(r'(ERR|WRN|EXCEPTION|ERROR|WARNING)', re.IGNORECASE)
        with open(main_log_path, 'w', encoding='utf-8') as main_f, \
             open(error_log_path, 'w', encoding='utf-8') as err_f:
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                line_stripped = line.strip()
                # Skip Shader spam lines
                if (line_stripped.startswith("WARNING: Shader") or
                    line_stripped.startswith("ERROR: Shader")):
                    continue
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                out_line = f"[{timestamp}] {line}"
                main_f.write(out_line)
                main_f.flush()
                prev_lines.append(out_line)
                # Publish join event if line contains "RequestToEnterGame:"
                if "RequestToEnterGame:" in line:
                    try:
                        # Example: "RequestToEnterGame: EOS_000202dfeabc4eb89ab17ea9bb69d77f/Lord Slaughter"
                        parts = line.split("RequestToEnterGame:")[1].strip().split("/")
                        if len(parts) >= 2:
                            steam_id = parts[0].strip()
                            player_name = parts[1].strip()
                            event = {
                                "type": "player_join",
                                "player": player_name,
                                "steam_id": steam_id,
                                "timestamp": timestamp
                            }
                            event_queue.put(event)
                        else:
                            print("Join event parse error: insufficient parts")
                    except Exception as e:
                        print("Error parsing join event:", e)
                # Publish leave event if line contains "disconnected" and "Player"
                if "disconnected" in line_stripped and "Player" in line_stripped:
                    try:
                        tokens = line_stripped.split()
                        if "Player" in tokens:
                            idx = tokens.index("Player")
                            if idx+1 < len(tokens):
                                player_name = tokens[idx+1]
                                event = {
                                    "type": "player_leave",
                                    "player": player_name,
                                    "timestamp": timestamp
                                }
                                event_queue.put(event)
                    except Exception as e:
                        print("Error parsing leave event:", e)
                # Write error log if line matches error_regex
                if error_regex.search(line_stripped):
                    for pline in prev_lines:
                        err_f.write(pline)
                    err_f.write("\n" * 5)
                    err_f.flush()
                    # Optionally clear the context: prev_lines.clear()

    async def read_response(reader, timeout=1.0):
        chunks = []
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(1024), timeout=timeout)
                if not chunk:
                    break
                chunks.append(chunk)
            except asyncio.TimeoutError:
                break
        return ''.join(chunks)

    async def authenticate_telnet(writer, reader):
        banner = ""
        while "Please enter password:" not in banner:
            chunk = await read_response(reader, timeout=1.0)
            if not chunk:
                break
            banner += chunk
        banner_stripped = banner.replace("Please enter password:", "")
        if banner_stripped.strip():
            print(banner_stripped, end='')
        writer.write(TELNET_PASSWORD + "\n")
        await writer.drain()
        post_auth = await read_response(reader, timeout=1.0)
        if post_auth.strip():
            print(post_auth, end='')
        print("Logon successful.")

    async def async_input(prompt: str) -> str:
        return await asyncio.get_running_loop().run_in_executor(None, input, prompt)

    async def handle_input(writer, reader):
        while True:
            command = await async_input("Enter command: ")
            cmd_lower = command.lower()
            if cmd_lower == "exit":
                writer.write("exit\n")
                await writer.drain()
                final_resp = await read_response(reader, timeout=1.0)
                if final_resp.strip():
                    print(final_resp, end='')
                break
            elif cmd_lower == "shutdown":
                writer.write("shutdown\n")
                await writer.drain()
                shutdown_resp = await read_response(reader, timeout=2.0)
                if shutdown_resp.strip():
                    print(shutdown_resp, end='')
                print("Waiting for the server to finish shutting down...")
                for _ in range(15):
                    chunk = await read_response(reader, timeout=1.0)
                    if chunk.strip():
                        print(chunk, end='')
                print("Server shutdown initiated. Exiting script now.")
                exit(0)
            else:
                writer.write(command + "\n")
                await writer.drain()
                response = await read_response(reader, timeout=1.5)
                if response.strip():
                    print(response, end='')

    async def start_server_task():
        os.chdir(server_path)
        log_timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        main_log_path = os.path.join(logs_dir, f"log_{log_timestamp}.txt")
        error_log_path = os.path.join(logs_dir, f"error_{log_timestamp}.txt")
        print(f"Starting server, main logs -> {main_log_path}")
        print(f"Error logs -> {error_log_path}")
        command = [
            executable,
            "-quit", "-batchmode", "-nographics",
            "-configfile=serverconfig.xml",
            "-dedicated"
        ]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True
            )
            t = threading.Thread(
                target=stream_logs_to_files,
                args=(process, main_log_path, error_log_path),
                daemon=True
            )
            t.start()
            threading.Thread(target=monitor_server, args=(process,), daemon=True).start()
            for _ in range(30):
                print("Connecting to Telnet...")
                try:
                    reader_telnet, writer_telnet = await telnetlib3.open_connection(
                        'localhost', TELNET_PORT, encoding='ascii'
                    )
                    await authenticate_telnet(writer_telnet, reader_telnet)
                    await handle_input(writer_telnet, reader_telnet)
                    break
                except ConnectionRefusedError:
                    await asyncio.sleep(1)
            else:
                print("Failed to connect to Telnet after multiple attempts.")
                return
        except Exception as e:
            print(f"Error launching the server: {e}")
            return
    asyncio.run(start_server_task())
    print("Returned from Telnet session. Server is still running in the background.")

def join_telnet():
    async def read_response(reader, timeout=1.0):
        chunks = []
        while True:
            try:
                chunk = await asyncio.wait_for(reader.read(1024), timeout=timeout)
                if not chunk:
                    break
                chunks.append(chunk)
            except asyncio.TimeoutError:
                break
        return ''.join(chunks)

    async def authenticate_telnet(writer, reader):
        banner = ""
        while "Please enter password:" not in banner:
            chunk = await read_response(reader, timeout=1.0)
            if not chunk:
                break
            banner += chunk
        banner_stripped = banner.replace("Please enter password:", "")
        if banner_stripped.strip():
            print(banner_stripped, end='')
        writer.write(TELNET_PASSWORD + "\n")
        await writer.drain()
        post_auth = await read_response(reader, timeout=1.0)
        if post_auth.strip():
            print(post_auth, end='')
        print("Logon successful.")

    async def async_input(prompt: str) -> str:
        return await asyncio.get_running_loop().run_in_executor(None, input, prompt)

    async def handle_input(writer, reader):
        while True:
            command = await async_input("Enter command: ")
            cmd_lower = command.lower()
            if cmd_lower == "exit":
                writer.write("exit\n")
                await writer.drain()
                final_resp = await read_response(reader, timeout=1.0)
                if final_resp.strip():
                    print(final_resp, end='')
                break
            elif cmd_lower == "shutdown":
                writer.write("shutdown\n")
                await writer.drain()
                shutdown_resp = await read_response(reader, timeout=2.0)
                if shutdown_resp.strip():
                    print(shutdown_resp, end='')
                print("Waiting for the server to finish shutting down...")
                for _ in range(15):
                    chunk = await read_response(reader, timeout=1.0)
                    if chunk.strip():
                        print(chunk, end='')
                print("Server shutdown initiated. Exiting script now.")
                exit(0)
            else:
                writer.write(command + "\n")
                await writer.drain()
                response = await read_response(reader, timeout=1.5)
                if response.strip():
                    print(response, end='')

    async def telnet_connect():
        for _ in range(30):
            print("Connecting to Telnet...")
            try:
                reader_telnet, writer_telnet = await telnetlib3.open_connection(
                    'localhost', TELNET_PORT, encoding='ascii'
                )
                await authenticate_telnet(writer_telnet, reader_telnet)
                await handle_input(writer_telnet, reader_telnet)
                break
            except ConnectionRefusedError:
                await asyncio.sleep(1)
        else:
            print("Failed to connect after multiple attempts.")
    asyncio.run(telnet_connect())
    print("Returned from Telnet console. (Server may still be running unless it was shut down.)")

def kill_server_processes():
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] in ['7DaysToDie.exe', '7DaysToDieServer.exe']:
            print(f"Killing process {proc.info['name']} with PID {proc.info['pid']}")
            proc.kill()

# --- Main ---
def main():
    while True:
        print("7 Days to Die Server Manager")
        print("============================")
        print("Choose an option:")
        print("")
        print("1. Install")
        print("2. Update")
        print("3. Start Server (and join Telnet)")
        print("4. Install C++ Redistributable")
        print("5. Exit (Kills server if running)")
        print("6. Join Telnet (Server must already be running)")
        choice = input("Enter your choice: ")
        if choice == "1":
            install()
        elif choice == "2":
            update()
        elif choice == "3":
            start()
        elif choice == "4":
            install_cpp_redistributable()
        elif choice == "5":
            kill_server_processes()
            break
        elif choice == "6":
            join_telnet()
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
