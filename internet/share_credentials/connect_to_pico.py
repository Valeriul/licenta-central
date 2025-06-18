import asyncio
import socket
from bleak import BleakScanner, BleakClient

# UUIDs for Nordic UART Service (NUS)
UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write
UART_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Notify

DEVICE_PREFIX = "LICN"  # Prefix for BLE devices to search for

def get_wifi_credentials():
    """Extracts the WiFi SSID and password from wpa_supplicant.conf"""
    try:
        with open("/etc/wpa_supplicant/wpa_supplicant.conf", "r") as file:
            content = file.readlines()
        
        ssid = None
        psk = None
        for line in content:
            if "ssid=" in line:
                ssid = line.split("=")[1].strip().strip('"')
            if "psk=" in line:
                psk = line.split("=")[1].strip().strip('"')

        if ssid and psk:
            return ssid, psk
        else:
            print("WiFi credentials not found.")
            return None, None

    except Exception as e:
        print(f"Error reading WiFi credentials: {e}")
        return None, None

def get_ip_address():
    """Retrieves the local IP address of the Pi."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        print(f"Error getting IP address: {e}")
        return "0.0.0.0"

async def find_licn_device():
    """Continuously scan for BLE devices whose names start with LICN."""
    print("Scanning for BLE devices with prefix LICN...")
    while True:
        devices = await BleakScanner.discover()

        for device in devices:
            if device.name and device.name.startswith(DEVICE_PREFIX):
                print(f"Found {device.name}: {device.address}")
                return device.address

        print("No LICN devices found. Retrying in 5 seconds...")
        await asyncio.sleep(5)  # Wait before scanning again

async def send_data(client, label, data):
    """Sends a labeled message (SSID, PASSWORD, IP) and waits for acknowledgment."""
    message = f"{label}:{data}\n"
    print(f"Sending: {message.strip()}")
    await client.write_gatt_char(UART_RX_CHAR_UUID, message.encode())
    await asyncio.sleep(2)  # Wait for Pico W acknowledgment

async def uart_communication():
    """Continuously looks for LICN devices and sends WiFi credentials."""
    while True:
        pico_address = await find_licn_device()
        if not pico_address:
            continue  # If no device found, restart the scan loop

        try:
            async with BleakClient(pico_address) as client:
                print(f"Connected to {pico_address}")

                def notification_handler(sender, data):
                    """Handles incoming BLE UART data from the Pico W."""
                    try:
                        message = data.decode()
                        print(f"Received from Pico: {message}")
                    except Exception as e:
                        print(f"Error decoding response: {e}")

                # Enable notifications
                await client.start_notify(UART_TX_CHAR_UUID, notification_handler)

                # Get real WiFi credentials and IP
                ssid, password = get_wifi_credentials()
                ip_address = get_ip_address()

                if not ssid or not password:
                    print("WiFi credentials are missing. Aborting BLE transmission.")
                    await client.disconnect()
                    continue  # Restart scanning for next LICN device

                # Send each piece of data separately
                await send_data(client, "SSID", ssid)
                await send_data(client, "PASSWORD", password)
                await send_data(client, "IP", ip_address)

                # Disconnect
                await client.stop_notify(UART_TX_CHAR_UUID)
                print(f"Disconnected from {pico_address}")

        except Exception as e:
            print(f"Connection failed: {e}")

        print("\n🔄 Restarting scan for new LICN devices...\n")

# Run the script
asyncio.run(uart_communication())
