from smartcard.System import readers
from smartcard.util import toHexString

# Data must be exactly 16 bytes (pad with spaces if needed)
data_to_write = b'ID0001GHS200.00E'  # Example: 16 bytes
auth_key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]  # Default Key A
block_number = 4  # Block 4 = Sector 1, first usable block

try:
    # Step 1: Get reader and connect
    r = readers()
    if len(r) < 1:
        raise Exception("No NFC reader found.")
    
    reader = r[0]
    connection = reader.createConnection()
    connection.connect()

    print(f"[+] Connected to: {reader}")

    # Step 2: Load Authentication Key
    load_key_cmd = [0xFF, 0x82, 0x00, 0x00, 0x06] + auth_key
    response, sw1, sw2 = connection.transmit(load_key_cmd)
    if sw1 != 0x90:
        raise Exception(f"[-] Failed to load key: {hex(sw1)} {hex(sw2)}")
    print("[+] Key loaded")

    # Step 3: Authenticate with Key A
    auth_cmd = [
        0xFF, 0x86, 0x00, 0x00, 0x05,  # Command structure
        0x01,  # Number of authentication blocks
        0x00,  # Block number MSB (most NFC cards use 0x00 here)
        block_number,  # Block to authenticate
        0x60,  # Type A key
        0x00   # Location in reader where key was loaded
    ]
    response, sw1, sw2 = connection.transmit(auth_cmd)
    if sw1 != 0x90:
        raise Exception(f"[-] Authentication failed: {hex(sw1)} {hex(sw2)}")
    print("[+] Authentication successful")

    # Step 4: Write Data (16 bytes only)
    if len(data_to_write) != 16:
        raise Exception("[-] Data must be exactly 16 bytes.")

    write_cmd = [0xFF, 0xD6, 0x00, block_number, 0x10] + list(data_to_write)
    response, sw1, sw2 = connection.transmit(write_cmd)
    if sw1 == 0x90 and sw2 == 0x00:
        print("[+] Data written successfully!")
    else:
        raise Exception(f"[-] Write failed: {hex(sw1)} {hex(sw2)}")

except Exception as e:
    print(str(e))
