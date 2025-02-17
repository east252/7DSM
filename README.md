# About

### 7 Days To Die Server Manager
7DSM by Primal Rage Gaming  
Version: 0.0.1  
Author: Njinir  
Created 2/2025  
Primal Rage Gaming

# Features
* Install steamcmd
* Install 7 Days to Die Server
* Installs are placed in the same directory for easy access
* Environmental Variable (.env) file for overriding serverconfig.xml
* Serverconfig.xml clean up and line up
* Start 7 Days to Die server and monitor for crashes
* Server Monitor will relaunch the game if it crashes
* Exit will exit the program and shut down the server
* Log filter for shader lines (remove from logs)
* Error log - an additional log for errors and 20 lines before it
* Simple log - adjusted logging for clarity
* Backup System - We use zst to handle large/fast backups
* Install the latest experimental version or stable version

# Prerequisites
1. Install python from microsoft store. 3.12 preferably.  
2. Install Visual C++ Redistributable "https://aka.ms/vs/17/release/vc_redist.x64.exe"  
3. Place the program (7DSM.py) in a folder (this is your working folder).
4. When steamcmd and server are installed, they will sit beside this folder.
5. Install the prerequisites using python.
6. Create a .env file in the working folder. (This is for your variables/settings)  
    NOTE: The .env file is customizable. Add any variables you want to change.
7. Use python's pip to install the prerequisites: python -m pip install -r requirements.txt

# Example .env file:
"""Server Config Variables"""
SERVERCONFIG_LandClaimCount="5"
SERVERCONFIG_LootAbundance="200"
SERVERCONFIG_GameDifficulty="3"
SERVERCONFIG_ServerName="Njinir"
SERVERCONFIG_ServerPassword="MySecretPassword123"
SERVERCONFIG_ServerMaxPlayerCount="10"
SERVERCONFIG_WebDashboardEnabled="true"
SERVERCONFIG_TerminalWindowEnabled="true"

"""Save file. Do not change this value."""
SERVERCONFIG_UserDataFolder="./UserDataFolder"

"""Backup Config Variables - if not top level, use _ to separate folders."""
BACKUPCONFIG_UserDataFolder="true"
BACKUPCONFIG_Logs="true"
BACKUPCONFIG_serverconfig.xml="true" 
BACKUPCONFIG_Mods="true" # This is the folder where you can place your custom mods.
BACKUPCONFIG_LocalPrefabs="true" # This is the folder where you can place your custom prefabs.
BACKUPCONFIG_Data_Worlds="true" # This is the folder where your worlds are stored.

""" Latest Experimental """ 
INSTALLCONFIG_Experimental="true" # This will install the latest experimental version of the server.

# File Setup
```
7DSM
    | -> server  
    | -> steamcmd  
    | -> .env  
    | -> 7DSM.py  
```


# Future Versions 

Task List
* Donor Buffer: Hold the last 10 slots for VIP's entering the game
* Donor Slot: A list of steamid, name, expiration date for VIPs
* Expired Landcaim Printout: Show where expired claims are in print
* Reset Region functionality
* Send server messages
* Save and backup system
* Discord Integration
* Web API integration
* Ping Ban for excessive ping
* Country Ban
* Player Teleports
* Give to player inventory
* Reset player level
* Reset player skills
* Custom zombie spawner for admins
* Automated server messages
* Vehicle retrieval (pull vehicle to player)