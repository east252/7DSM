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

# Load environment variables from .env file
load_dotenv()


TELNET_PORT = int(os.getenv("TELNET_PORT"))
TELNET_PASSWORD = os.getenv("TELNET_PASSWORD").strip()

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

def apply_env_overrides(config_file):
    import xml.etree.ElementTree as ET
    tree = ET.parse(config_file)
    root = tree.getroot()

    for key, raw_value in os.environ.items():
        if key.startswith("SERVERCONFIG_"):
            # Windows might uppercase the entire var name, so ignore case:
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
                print(f"WARNING: No property found for env var '{key}' => "
                      f"looking for name='{env_config_name}' in serverconfig.xml")

    tree.write(config_file)
    print(f"Done applying .env overrides to {config_file}.")


def install_cpp_redistributable():
    url = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    installer_path = "vc_redist.x64.exe"

    # Download the installer
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

    # Run the installer
    print("Installing C++ Redistributable...")
    try:
        subprocess.run([installer_path, '/install', '/quiet', '/norestart'], check=True)
        print("Installation complete.")
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        return

    # Clean up the installer file
    os.remove(installer_path)
    print("Installer file removed.")

def update():
    steamcmd_dir = "steamcmd"
    steamcmd_path = os.path.join(steamcmd_dir, "steamcmd.exe")

    # Check if steamcmd is installed
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

    # Check if steamcmd is already installed
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
    Starts the 7DTD server AND immediately connects to Telnet.
    'exit' in Telnet returns to main menu, server runs in background.
    'shutdown' in Telnet gracefully shuts down server, then script exits.
    """
    apply_env_overrides("server/serverconfig.xml") # Apply overrides before starting server
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

    tree = ET.parse(config_file)
    root = tree.getroot()
    for prop in root.findall('property'):
        if prop.get('name') == 'TelnetEnabled':
            prop.set('value', 'true')
        elif prop.get('name') == 'TelnetPort':
            prop.set('value', str(TELNET_PORT))
        elif prop.get('name') == 'TelnetPassword':
            prop.set('value', TELNET_PASSWORD)

    for key, value in os.environ.items():
        if key.startswith("SERVERCONFIG_"):
            config_name = key[len("SERVERCONFIG_"):]
            for prop in root.findall('property'):
                if prop.get('name') == config_name:
                    prop.set('value', value)
                    print(f"Updated {config_name} to {value} in serverconfig.xml")

    tree.write(config_file)

    def monitor_server(process):
        while True:
            if process.poll() is not None:
                print("Server process terminated. Restarting...")
                asyncio.run(start_server_task())
                break
            time.sleep(5)

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
        """
        Read banner until 'Please enter password:' is found (but don't show that line),
        then send password, read post-auth, and print 'Logon successful.'.
        """
        banner = ""
        while "Please enter password:" not in banner:
            chunk = await read_response(reader, timeout=1.0)
            if not chunk:
                break
            banner += chunk

        # Remove "Please enter password:" from output
        banner_stripped = banner.replace("Please enter password:", "")
        if banner_stripped.strip():
            print(banner_stripped, end='')

        # Send password
        writer.write(TELNET_PASSWORD + "\n")
        await writer.drain()

        # Print anything after password is sent
        post_auth = await read_response(reader, timeout=1.0)
        if post_auth.strip():
            print(post_auth, end='')

        # Then print "Logon successful."
        print("Logon successful.")

    async def async_input(prompt: str) -> str:
        return await asyncio.get_running_loop().run_in_executor(None, input, prompt)

    async def handle_input(writer, reader):
        while True:
            command = await async_input("Enter command: ")
            cmd_lower = command.lower()

            # exit -> return to main menu
            if cmd_lower == "exit":
                writer.write("exit\n")
                await writer.drain()
                final_resp = await read_response(reader, timeout=1.0)
                if final_resp.strip():
                    print(final_resp, end='')
                break

            # shutdown -> graceful
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

            # normal command
            else:
                writer.write(command + "\n")
                await writer.drain()
                response = await read_response(reader, timeout=1.5)
                if response.strip():
                    print(response, end='')

    async def start_server_task():
        os.chdir(server_path)
        log_timestamp = time.strftime("__%Y-%m-%d__%H-%M-%S")
        log_file = os.path.join(logs_dir, f"output_log{log_timestamp}.txt")
        print(f"Writing log file to: {log_file}")

        command = [
            executable,
            "-logfile", log_file,
            "-quit", "-batchmode", "-nographics",
            "-configfile=serverconfig.xml",
            "-dedicated"
        ]

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True
            )
            threading.Thread(target=monitor_server, args=(process,), daemon=True).start()

            # Instead of "Telnet connection refused, retrying..." we just say "Connecting to Telnet..."
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
    """
    Connect to an already-running server. 
    'exit' returns to main menu, 'shutdown' gracefully ends server (then exits script).
    """
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

if __name__ == "__main__":
    main()
