# Install Python before running this script.
# Author: Njinir

# pip install requests
# 7 Days requires the lastest C++ Redistributable: 
#   https://docs.microsoft.com/en-US/cpp/windows/latest-supported-vc-redist?view=msvc-170

import os
import zipfile
import requests
import subprocess
import shutil
import time

def main():
    while True:
        print("7 Days to Die Server Manager")
        print("============================")
        print("Choose an option:")
        print("")
        print("1. Install")
        print("2. Update")
        print("3. Start")
        print("4. Install C++ Redistributable")
        print("5. Exit")
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
            break
        else:
            print("Invalid choice. Try again.")

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

    # Calculate the path for the Server directory one level up
    install_dir = os.path.abspath(os.path.join(os.path.dirname(steamcmd_path), '..', 'Server'))

    try:
        # Launch the command and get stdout and stderr in real-time
        process = subprocess.Popen(
            [steamcmd_path, '+force_install_dir', install_dir, '+login', 'anonymous', '+app_update', '294420', '+quit'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print output line by line
        for line in process.stdout:
            print(line, end='')  # Print each line from stdout as it's generated
        
        # Wait for the process to finish
        process.wait()
        
        # Check if there were errors
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
        # Proceed to the launch and install steps
        launch_and_install(steamcmd_path)
        return
    
    # Step 1: Download steamcmd.zip
    url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
    zip_path = "steamcmd.zip"
    print("Downloading steamcmd.zip...")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Will raise an error for 4xx/5xx status codes
        with open(zip_path, 'wb') as file:
            file.write(response.content)
        print("Download complete.")
    except requests.RequestException as e:
        print(f"Download failed: {e}")
        return
    
    # Step 2: Unzip the file and delete the zip
    print("Extracting steamcmd...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(steamcmd_dir)
        os.remove(zip_path)  # Delete the zip file
        print("Extraction complete.")
    except zipfile.BadZipFile as e:
        print(f"Error extracting the zip file: {e}")
        return

    # Step 3: Proceed to the launch and install steps
    launch_and_install(steamcmd_path)

def launch_and_install(steamcmd_path):
    # Ensure that steamcmd.exe exists in the folder
    if not os.path.exists(steamcmd_path):
        print("steamcmd.exe not found.")
        return
    
    print("Launching steamcmd and installing 7 Days to Die...")

    # Calculate the path for the Server directory one level up
    install_dir = os.path.abspath(os.path.join(os.path.dirname(steamcmd_path), '..', 'Server'))
    
    try:
        # Launch the command and get stdout and stderr in real-time
        process = subprocess.Popen(
            [steamcmd_path, '+force_install_dir', install_dir, '+login', 'anonymous', '+app_update', '294420', '+quit'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Print output line by line
        for line in process.stdout:
            print(line, end='')  # Print each line from stdout as it's generated
        
        # Wait for the process to finish
        process.wait()
        
        # Check if there were errors
        if process.returncode != 0:
            print(f"Error during installation: {process.stderr.read()}")
        else:
            print("7 Days to Die installation complete.")
    
    except Exception as e:
        print(f"Error launching steamcmd: {e}")
        return

    print("Returning to main menu.")

def start():
    # Path to the 7 Days to Die Dedicated Server executable
    server_path = os.path.join("Server")
    executable = os.path.join(server_path, "7DaysToDieServer.exe")
    
    # Check if the dedicated server executable exists, if not, fall back to 7DaysToDie.exe
    if not os.path.exists(executable):
        executable = os.path.join(server_path, "7DaysToDie.exe")
        if not os.path.exists(executable):
            print("Error: Neither 7DaysToDieServer.exe nor 7DaysToDie.exe found.")
            return

    # Set log file timestamp similar to the batch script
    log_timestamp = time.strftime("__%Y-%m-%d__%H-%M-%S")
    log_file = os.path.join(server_path, f"{executable.split(os.sep)[-1]}_Data", f"output_log{log_timestamp}.txt")

    print(f"Writing log file to: {log_file}")

    # Build the command to launch the server
    command = [
        executable,
        "-logfile", log_file,
        "-quit", "-batchmode", "-nographics", 
        "-configfile", "serverconfig.xml", 
        "-dedicated"
    ]

    # Start the server process
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Capture and print stdout in real-time
        print("Starting server...")
        for line in process.stdout:
            print(line, end='')

        # Wait for the process to finish (server might run indefinitely)
        process.wait()
        
        # Check for errors
        if process.returncode != 0:
            print(f"Error starting server: {process.stderr.read()}")
        else:
            print("Server started successfully.")
        
    except Exception as e:
        print(f"Error launching the server: {e}")
        return

    print("Server running in background, you can close this window.")
    print("You can check the task manager to confirm the server process is running.")
    print("Press any key to return to the main menu.")

if __name__ == "__main__":
    main()