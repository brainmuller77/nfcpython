from smartcard.System import readers
from smartcard.util import toHexString

# Set block to read (Block 4 = Sector 1, start of usable blocks)
block_number = 4
auth_key = [0xFF] * 6  # Default Key A: FFFFFFFFFFFF

try:
    # Step 1: Connect to reader
    r = readers()
    if not r:
        raise Exception("[-] No NFC reader found.")
    
    reader = r[0]
    connection = reader.createConnection()
    connection.connect()
    print(f"[+] Connected to: {reader}")

    # Step 2: Load Key A into reader memory
    load_key_cmd = [0xFF, 0x82, 0x00, 0x00, 0x06] + auth_key
    response, sw1, sw2 = connection.transmit(load_key_cmd)
    if sw1 != 0x90:
        raise Exception(f"[-] Load key failed: {hex(sw1)} {hex(sw2)}")
    print("[+] Key loaded")

    # Step 3: Authenticate block with Key A
    auth_cmd = [
        0xFF, 0x86, 0x00, 0x00, 0x05,
        0x01, 0x00, block_number, 0x60, 0x00  # 0x60 = Key A
    ]
    response, sw1, sw2 = connection.transmit(auth_cmd)
    if sw1 != 0x90:
        raise Exception(f"[-] Authentication failed: {hex(sw1)} {hex(sw2)}")
    print("[+] Authentication successful")

    # Step 4: Read 16 bytes from the block
    read_cmd = [0xFF, 0xB0, 0x00, block_number, 0x10]
    response, sw1, sw2 = connection.transmit(read_cmd)
    if sw1 == 0x90 and sw2 == 0x00:
        print("[+] Read successful")
        print("[+] Raw bytes:", response)
        print("[+] As ASCII:", ''.join(chr(b) if 32 <= b < 127 else '.' for b in response))
    else:
        raise Exception(f"[-] Read failed: {hex(sw1)} {hex(sw2)}")

except Exception as e:
    print("Error:", e)
