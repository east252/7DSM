# 7 Days Server Manager
# Author: Njinir
# Created: 2025
# Primal Rage Gaming

# This is a Python script for a 7 Days to Die server manager. 
# It uses the 7 Days to Die server API to manage the server. 
# It can start, stop, restart, and update the server. 
# It can also send commands to the server and get the server status.

""" TODO: Prerequisites:
1. Install python from microsoft store. 3.12 preferably.  
2. Install Visual C++ Redistributable "https://aka.ms/vs/17/release/vc_redist.x64.exe"  
3. Place the program (7DSM.py) in a folder (this is your working folder).
4. When steamcmd and server are installed, they will sit beside this folder.
5. Install the prerequisites using python.
"""

""" Python Prerequisites:
via consle: pip install certifi, chardet, idna, psutil, python-dotenv, requests, telnetlib3, urllib3
"""

# Libraries


# Global Variables

    # Telnet Variables
TELNET_PORT="8081"
TELNET_PASSWORD="MySecretPassword123"

    # Server Config Variables
SERVERCONFIG_LandClaimCount="5"
SERVERCONFIG_LootAbundance="200"
SERVERCONFIG_GameDifficulty="3"
SERVERCONFIG_ServerName="Njinir"
SERVERCONFIG_ServerPassword="MySecretPassword123"
SERVERCONFIG_ServerMaxPlayerCount="10"
SERVERCONFIG_WebDashboardEnabled="true"
SERVERCONFIG_TerminalWindowEnabled="true"
SERVERCONFIG_UserDataFolder="./UserDataFolder"

    # Donor Buffer Settings
DONORBUFFER_ENABLED="true"
DONORBUFFER_SLOTS="10"

    # Server Messages


    # Server Settings


    # Server Manager Commands
SM_Donorlist = "donorlist"
SM_DonorBuffer = "donorbuffer"
SM_SetDonorBuffer = "setdonorbuffer"

# Functions / Definitions

def install():
    pass

def update():
    pass

def start():
    pass

def join():
    pass

def stop():
    pass

def restart():
    pass

def server_monitor():
    pass

def server_backup():
    pass

def server_logging():
    pass

def vip_list_load():
    pass

def telnet_connect():
    pass

def telnet_disconnect():
    pass

def telnet_send_command(command):
    pass

def server_config_override():
    pass








# Main
def main():
    while True:
        print("7 Days to Die Server Manager")
        print("============================")
        print("Choose an option:")
        print("")
        print("1. Install")
        print("2. Update")
        print("3. Start Server")
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
- [] virtual environment
- [] gitignore the steamcmd and server files
- [] install server beside, not in, the steamcmd folder
- [] allow install of prerequisites from SM menu.
- [] enforce telnet true, port, pass from .env file
- [] allow update of the server, include validate
- [] allow overwrite serverconfig.xml from .env
- [] log stamp and flow all logs from server to file
- [] ignore or remove WARNING: Shader and ERROR: Shader lines
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