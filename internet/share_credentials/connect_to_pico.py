import asyncio
import socket
from bleak import BleakScanner, BleakClient
import subprocess
import os
import configparser

# UUIDs for Nordic UART Service (NUS)
UART_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write
UART_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Notify

DEVICE_PREFIX = "LICN"  # Prefix for BLE devices to search for
CONNECTION_TIMEOUT = 120  # Timeout for BLE connection attempts in seconds

def get_wifi_credentials():
    """Robust version that handles all password types and formats"""
    try:
        # Method 1: Try to get credentials using nmcli directly (most reliable)
        print("Attempting to get credentials using nmcli...")
        
        # Get active WiFi connection name
        cmd = ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        wifi_connection = None
        for line in result.stdout.strip().split('\n'):
            if line.endswith(':802-11-wireless'):
                wifi_connection = line.split(':')[0]
                break
        
        if not wifi_connection:
            print("No active WiFi connection found")
            return None, None
        
        print(f"Active WiFi connection: {wifi_connection}")
        
        # Try to get password directly from nmcli (works for most cases)
        try:
            cmd = ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', wifi_connection]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            password_from_nmcli = result.stdout.strip()
            
            # Get SSID from nmcli too
            cmd = ['nmcli', '-g', '802-11-wireless.ssid', 'connection', 'show', wifi_connection]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            ssid_from_nmcli = result.stdout.strip()
            
            if password_from_nmcli and ssid_from_nmcli:
                print(f"✅ Got credentials from nmcli directly")
                print(f"SSID: '{ssid_from_nmcli}' (length: {len(ssid_from_nmcli)})")
                print(f"Password length: {len(password_from_nmcli)}")
                return ssid_from_nmcli, password_from_nmcli
                
        except subprocess.CalledProcessError:
            print("Direct nmcli method failed, trying file parsing...")
        
        # Method 2: Parse the connection file (fallback)
        file_path = f"/etc/NetworkManager/system-connections/{wifi_connection}.nmconnection"
        
        # Try different encodings to handle special characters
        encodings = ['utf-8', 'latin-1', 'cp1252']
        content = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                print(f"✅ Successfully read file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if not content:
            print("❌ Could not read file with any encoding")
            return None, None
        
        # Parse for SSID and password with multiple fallback methods
        ssid = None
        password = None
        
        # Try configparser first (handles quotes and escaping properly)
        try:
            import io
            config = configparser.ConfigParser()
            config.read_string(content)
            
            if 'wifi' in config and 'ssid' in config['wifi']:
                ssid = config['wifi']['ssid']
            if 'wifi-security' in config and 'psk' in config['wifi-security']:
                password = config['wifi-security']['psk']
                
        except Exception as e:
            print(f"ConfigParser failed: {e}, trying manual parsing...")
        
        # Manual parsing as fallback
        if not ssid or not password:
            for line in content.split('\n'):
                line = line.strip()
                
                if line.startswith('ssid=') and not ssid:
                    ssid = line.split('=', 1)[1]
                    # Handle different quote styles
                    ssid = _clean_credential_value(ssid)
                    
                elif line.startswith('psk=') and not password:
                    password = line.split('=', 1)[1]
                    # Handle different quote styles and escaping
                    password = _clean_credential_value(password)
        
        # Validate and return
        if ssid and password:
            print(f"✅ SSID: '{ssid}' (length: {len(ssid)})")
            print(f"✅ Password length: {len(password)}")
            # Don't print actual password for security
            return ssid, password
        else:
            print(f"❌ Missing credentials - SSID: {bool(ssid)}, Password: {bool(password)}")
            return None, None
        
    except FileNotFoundError:
        print(f"❌ Connection file not found: {file_path}")
        return None, None
    except PermissionError:
        print("❌ Permission denied. Run with sudo.")
        return None, None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

def _clean_credential_value(value):
    """Clean and properly decode credential values from config files"""
    if not value:
        return value
    
    # Strip whitespace
    value = value.strip()
    
    # Handle different quote styles
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    
    # Handle escaped characters
    value = value.replace('\\n', '\n')
    value = value.replace('\\t', '\t')
    value = value.replace('\\r', '\r')
    value = value.replace('\\"', '"')
    value = value.replace("\\'", "'")
    value = value.replace('\\\\', '\\')
    
    return value

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

        print("No LICN devices found. Retrying in 2 seconds...")
        await asyncio.sleep(2)  # Wait before scanning again

async def send_data(client, label, data):
    """Sends a labeled message (SSID, PASSWORD, IP) - simple and reliable."""
    # Create message - keep it simple
    message = f"{label}:{data}\n"
    
    print(f"=== SENDING {label} ===")
    print(f"Raw data: '{data}'")
    print(f"Data length: {len(data)} characters")
    print(f"Complete message: '{message}'")
    print(f"Message length: {len(message)} characters")
    
    try:
        # Convert to bytes
        message_bytes = message.encode('utf-8')
        print(f"Encoded bytes length: {len(message_bytes)}")
        print(f"Bytes hex: {message_bytes.hex()}")
        print(f"Bytes as list: {list(message_bytes)}")
        
        # For longer messages, send in smaller chunks to ensure reliability
        chunk_size = 20  # Conservative chunk size for BLE
        
        if len(message_bytes) <= chunk_size:
            # Send as single message
            await client.write_gatt_char(UART_RX_CHAR_UUID, message_bytes)
            print(f"✅ Sent as single message")
        else:
            # Send in small chunks
            print(f"📦 Sending in chunks of {chunk_size} bytes...")
            for i in range(0, len(message_bytes), chunk_size):
                chunk = message_bytes[i:i + chunk_size]
                print(f"   Chunk {i//chunk_size + 1}: {len(chunk)} bytes - {chunk.hex()}")
                await client.write_gatt_char(UART_RX_CHAR_UUID, chunk)
                await asyncio.sleep(0.1)  # Small delay between chunks
        
        print(f"✅ Successfully wrote to BLE characteristic")
        await asyncio.sleep(3)  # Longer wait for acknowledgment
        
    except Exception as e:
        print(f"❌ Error sending {label}: {e}")
        raise

async def connect_and_send_data(pico_address, ssid, password):
    """Attempt to connect to device and send data with timeout."""
    try:
        print(f"Attempting to connect to {pico_address} (timeout: {CONNECTION_TIMEOUT}s)...")
        
        # Use asyncio.wait_for to implement the 30-second timeout
        async with asyncio.timeout(CONNECTION_TIMEOUT):
            async with BleakClient(pico_address) as client:
                print(f"✅ Successfully connected to {pico_address}")

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
                ip_address = get_ip_address()

                if not ssid or not password:
                    print("WiFi credentials are missing. Aborting BLE transmission.")
                    return False

                # Send each piece of data separately
                await send_data(client, "SSID", ssid)
                await send_data(client, "PASSWORD", password)
                await send_data(client, "IP", ip_address)

                # Disconnect
                await client.stop_notify(UART_TX_CHAR_UUID)
                print(f"✅ Successfully sent data and disconnected from {pico_address}")
                return True

    except asyncio.TimeoutError:
        print(f"❌ Connection to {pico_address} timed out after {CONNECTION_TIMEOUT} seconds")
        return False
    except Exception as e:
        print(f"❌ Connection to {pico_address} failed: {e}")
        return False

async def uart_communication(ssid, password):
    """Continuously looks for LICN devices and sends WiFi credentials."""
    while True:
        pico_address = await find_licn_device()
        if not pico_address:
            continue  # If no device found, restart the scan loop

        # Attempt connection with longer timeout
        success = await connect_and_send_data(pico_address, ssid, password)
        
        if success:
            print("✅ Data transmission completed successfully")
        else:
            print("❌ Failed to connect or send data")

        print("\n🔄 Restarting scan for new LICN devices...\n")

# Run the script
ssid, password = get_wifi_credentials()
if not ssid or not password:
    print("WiFi credentials are missing. Please ensure you are connected to a WiFi network.")
    exit(1)
asyncio.run(uart_communication(ssid, password))