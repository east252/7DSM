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
    The path is calculated relative to the script's directory.
    """
    vip_set = set()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vip_path = os.path.join(base_dir, vip_file)
    try:
        with open(vip_path, "r") as f:
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
    Increments the global player count.
    When the donor buffer is active, if the joining player’s Steam ID is not on the VIP list,
    the persistent Telnet connection sends a kick command using the player's name.
    Minimal logging is printed.
    """
    global current_player_count
    player = event.get("player")
    steam_id = event.get("steam_id")
    current_player_count += 1
    # (Reduced verbosity: Only print a minimal message)
    if DONORBUFFER_ENABLED and current_player_count >= (MAX_PLAYERS - DONORBUFFER_SLOTS):
        vip_list = load_vip_list()
        if steam_id not in vip_list:
            print(f"Donor buffer active: kicking {player}")
            send_telnet_command(f'kick "{player}" "We are at max capacity. Only VIPs may join at this time. Sorry for the inconvenience"')

        else:
            print(f"{player} is VIP, allowed.")
    # Otherwise, no extra output

def handle_player_leave(event):
    """
    Handles a player leave event.
    Decrements the global player count.
    """
    global current_player_count
    player = event.get("player")
    current_player_count = max(0, current_player_count - 1)
    # Minimal logging; omit verbose prints.

# --- Persistent Telnet Connection ---
class PersistentTelnetClient:
    """
    This class maintains a persistent Telnet connection.
    It runs a command loop that processes commands from an internal asyncio queue.
    """
    def __init__(self, host, port, encoding="ascii"):
        self.host = host
        self.port = port
        self.encoding = encoding
        self.reader = None
        self.writer = None
        self.command_queue = asyncio.Queue()
        self.running = False
        self.loop = asyncio.new_event_loop()

    async def connect(self):
        try:
            self.reader, self.writer = await telnetlib3.open_connection(self.host, self.port, encoding=self.encoding)
            # Send password for authentication
            self.writer.write(TELNET_PASSWORD + "\n")
            await self.writer.drain()
            # Optionally, read authentication response
            auth_resp = await asyncio.wait_for(self.reader.read(1024), timeout=2.0)
            print("Persistent Telnet connected and authenticated.\nEnter Command: ")
            self.running = True
        except Exception as e:
            print(f"Error establishing persistent Telnet connection: {e}")

    async def command_loop(self):
        """
        Continuously processes commands from the internal queue.
        """
        while self.running:
            cmd = await self.command_queue.get()
            if not self.running:
                break
            self.writer.write(cmd + "\n")
            await self.writer.drain()
            try:
                response = await asyncio.wait_for(self.reader.read(1024), timeout=2.0)
                # You can further process or log the response if desired.
                print(f"Response for '{cmd}': {response.strip()}")
            except asyncio.TimeoutError:
                print(f"No response for command '{cmd}'.")
            self.command_queue.task_done()

    async def send_command(self, cmd):
        """
        Schedules a command to be sent over the persistent connection.
        """
        await self.command_queue.put(cmd)

    async def close(self):
        self.running = False
        self.writer.close()

    def start(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.connect())
        self.loop.create_task(self.command_loop())
        self.loop.run_forever()

# Global persistent telnet client instance
persistent_telnet_client = None

def start_persistent_telnet():
    """
    Starts the persistent Telnet client in its own thread.
    """
    global persistent_telnet_client
    persistent_telnet_client = PersistentTelnetClient('localhost', TELNET_PORT)
    thread = threading.Thread(target=persistent_telnet_client.start, daemon=True)
    thread.start()

# --- Telnet Command Function ---
def send_telnet_command(command):
    """
    Sends a Telnet command using the persistent connection.
    If the persistent connection is not available, logs an error.
    """
    if persistent_telnet_client and persistent_telnet_client.running:
        asyncio.run_coroutine_threadsafe(persistent_telnet_client.send_command(command), persistent_telnet_client.loop)
    else:
        print(f"Persistent Telnet connection not available. Command: {command}")

# --- Hybrid Player Count Polling ---
async def read_response_global(reader, timeout=1.0):
    chunks = []
    try:
        while True:
            chunk = await asyncio.wait_for(reader.read(1024), timeout=timeout)
            if not chunk:
                break
            chunks.append(chunk)
    except asyncio.TimeoutError:
        pass
    return ''.join(chunks)

async def get_player_count_from_server():
    try:
        reader, writer = await telnetlib3.open_connection('localhost', TELNET_PORT, encoding='ascii')
        writer.write("le\n")
        await writer.drain()
        response = await read_response_global(reader, timeout=2.0)
        writer.close()
        match = re.search(r"Total of (\d+) in the game", response)
        if match:
            return int(match.group(1))
        else:
            lines = response.splitlines()
            count = sum(1 for line in lines if re.match(r"^\d+\.\s+id=", line))
            return count
    except Exception as e:
        print(f"Error polling player count: {e}")
        return None

def poll_player_count():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    global current_player_count
    while True:
        count = loop.run_until_complete(get_player_count_from_server())
        if count is not None:
            if current_player_count != count:
                print(f"Reconciled player count: {count} (was {current_player_count})")
                current_player_count = count
        time.sleep(30)  # poll every 30 seconds

# --- Existing Functions (Install, Update, etc.) ---
def apply_env_overrides(config_file):
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
    Starts the 7DTD server WITHOUT '-logfile', capturing logs to files.
    After starting, it establishes a persistent Telnet connection for interactive command input.
    """
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
        while True:
            if process.poll() is not None:
                print("Server process terminated. Restarting...")
                asyncio.run(start_server_task())
                break
            time.sleep(5)

    def stream_logs_to_files(proc, main_log_path, error_log_path):
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
                if (line_stripped.startswith("WARNING: Shader") or
                    line_stripped.startswith("ERROR: Shader")):
                    continue
                timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
                out_line = f"[{timestamp}] {line}"
                main_f.write(out_line)
                main_f.flush()
                prev_lines.append(out_line)
                if "RequestToEnterGame:" in line:
                    try:
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
                if error_regex.search(line_stripped):
                    for pline in prev_lines:
                        err_f.write(pline)
                    err_f.write("\n" * 5)
                    err_f.flush()

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

    async def handle_input():
        """
        Uses the persistent Telnet connection for interactive command input.
        """
        while True:
            command = await async_input("Enter command: ")
            cmd_lower = command.lower()
            if cmd_lower == "exit":
                await persistent_telnet_client.send_command("exit")
                break
            elif cmd_lower == "shutdown":
                await persistent_telnet_client.send_command("shutdown")
                print("Waiting for the server to finish shutting down...")
                exit(0)
            else:
                await persistent_telnet_client.send_command(command)

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
            threading.Thread(target=poll_player_count, daemon=True).start()
            # Start persistent Telnet connection
            start_persistent_telnet()
            await asyncio.sleep(2)  # Wait briefly for connection establishment
            await handle_input()
            # Optionally, close the persistent connection here.
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
                reader_telnet, writer_telnet = await telnetlib3.open_connection('localhost', TELNET_PORT, encoding='ascii')
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
    """
    Sends a graceful shutdown command via Telnet, waits briefly, then force-kills processes if needed.
    """
    if persistent_telnet_client and persistent_telnet_client.running:
        print("Sending shutdown command to the server...")
        asyncio.run_coroutine_threadsafe(persistent_telnet_client.send_command("shutdown"), persistent_telnet_client.loop)
        time.sleep(5)  # Give the server time to shut down gracefully
    
    print("Checking if server processes are still running...")
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] in ['7DaysToDie.exe', '7DaysToDieServer.exe']:
            print(f"Killing process {proc.info['name']} with PID {proc.info['pid']}")
            proc.kill()

    print("Server has been shut down.")
    exit(0)  # Ensure the script exits cleanly after shutdown


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
        print("4. Join Telnet (Server must already be running)")
        print("9. Exit (Kills server if running)")
        choice = input("Enter your choice: ")
        if choice == "1":
            install()
        elif choice == "2":
            update()
        elif choice == "3":
            start()
        elif choice == "4":
            join_telnet()
        elif choice == "9":
            kill_server_processes()
        else:
            print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
