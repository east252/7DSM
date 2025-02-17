import asyncio
import telnetlib3

TELNET_HOST = "127.0.0.1"
TELNET_PORT = 8081
TELNET_PASSWORD = "MySecretPassword123"

class TelnetClient:
    def __init__(self, host, port, password):
        self.host = host
        self.port = port
        self.password = password
        self.reader = None
        self.writer = None
        self.connected = False
        self.stop_event = asyncio.Event()

    async def connect(self):
        self.reader, self.writer = await telnetlib3.open_connection(
            self.host, self.port, shell=self.shell
        )
        self.connected = True
        print("Connected to the server.")
        await self.authenticate()
        asyncio.create_task(self.shell(self.reader, self.writer))

    async def authenticate(self):
        self.writer.write(self.password + "\n")
        await self.writer.drain()
        print("Authenticated with the server.")

    async def shell(self, reader, writer):
        while not self.stop_event.is_set():
            outp = await reader.read(1024)
            if outp:
                print(outp, end='\nEnter Command: ')

    async def send_command(self, command):
        if self.writer:
            self.writer.write(command + "\n")
            await self.writer.drain()
            print(f"Sent command: {command}")

    async def disconnect(self):
        self.connected = False
        self.stop_event.set()
        if self.writer:
            self.writer.close()
            await asyncio.sleep(0.5)  # Give some time for the writer to close
            print("Disconnected from the server.")

async def menu(client):
    while True:
        print("\nMenu:")
        print("1. Send Command")
        print("2. Exit")
        choice = input("Select an option: ")

        if choice == "1":
            command = input("Enter Command: ")
            await client.send_command(command)
            await asyncio.sleep(1)  # Give some time for the server to respond
        elif choice == "2":
            await client.disconnect()
            break
        else:
            print("Invalid option. Please try again.")

async def main():
    client = TelnetClient(TELNET_HOST, TELNET_PORT, TELNET_PASSWORD)
    await client.connect()

    # Run the menu
    await menu(client)

if __name__ == "__main__":
    asyncio.run(main())