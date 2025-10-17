import urllib.request
import sys

# Asset type definitions
ASSET_TYPES = {
    0x0000: "BTC (Bitcoin)",
    0x0001: "BTC (Bitcoin - Satoshinet)", 
    0x0002: "BHASH (BHASH Protocol Asset Type)",
}

def get_asset_type_name(asset_type):
    """Get human-readable asset type name."""
    if asset_type in ASSET_TYPES:
        return ASSET_TYPES[asset_type]
    elif 0x0003 <= asset_type <= 0xFFFF:
        return f"Reserved Extension (0x{asset_type:04x})"
    else:
        return f"Unknown Type (0x{asset_type:04x})"

def fetch_tx_hex(txid):
    """Fetch raw transaction hex from mempool.space API."""
    url = f"https://mempool.space/api/tx/{txid}/hex"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 200:
                return response.read().decode().strip()
            else:
                print(f"❌ API returned HTTP status: {response.status}")
                return None
    except Exception as e:
        print(f"❌ Failed to fetch transaction: {e}")
        return None

def parse_varint(hex_str, offset):
    """Parse Bitcoin variable-length integer (varint)."""
    first = int(hex_str[offset:offset+2], 16)
    offset += 2
    if first < 0xFD:
        return first, offset
    elif first == 0xFD:
        val = int.from_bytes(bytes.fromhex(hex_str[offset:offset+4]), 'little')
        return val, offset + 4
    elif first == 0xFE:
        val = int.from_bytes(bytes.fromhex(hex_str[offset:offset+8]), 'little')
        return val, offset + 8
    else:  # 0xFF
        val = int.from_bytes(bytes.fromhex(hex_str[offset:offset+16]), 'little')
        return val, offset + 16

def extract_vout_scripts(tx_hex):
    """
    Extract all scriptPubKey hex strings from a raw transaction.
    Supports both legacy and SegWit (BIP144) transactions.
    """
    pos = 0
    data = tx_hex

    # Version (4 bytes)
    pos += 8

    # Check for SegWit marker (0x00) and flag (0x01)
    is_segwit = False
    if data[pos:pos+2] == '00' and data[pos+2:pos+4] == '01':
        is_segwit = True
        pos += 4  # Skip marker and flag

    # Input count
    input_count, pos = parse_varint(data, pos)

    # Skip all inputs
    for _ in range(input_count):
        pos += 64  # txid (32 bytes)
        pos += 8   # vout index (4 bytes)
        script_len, pos = parse_varint(data, pos)
        pos += script_len * 2  # scriptSig
        pos += 8   # sequence (4 bytes)

    # Output count
    output_count, pos = parse_varint(data, pos)

    # Parse all outputs
    scripts = []
    for _ in range(output_count):
        pos += 16  # value (8 bytes, 16 hex chars)
        script_len, pos = parse_varint(data, pos)
        script = data[pos:pos + script_len * 2]
        pos += script_len * 2
        scripts.append(script)

    # If SegWit, skip witness data (not needed for OP_RETURN)
    if is_segwit:
        for _ in range(input_count):
            witness_count, pos = parse_varint(data, pos)
            for __ in range(witness_count):
                item_len, pos = parse_varint(data, pos)
                pos += item_len * 2  # Skip each witness item

    # Locktime (4 bytes) is ignored
    return scripts

def parse_bhash_from_script(script_hex):
    """
    Parse BHASH protocol OP_RETURN from scriptPubKey hex.
    Expected format: 6a <push_len> 91 <39 more bytes>
    Payload must be at least 40 bytes starting with 0x91.
    """
    if not script_hex.startswith('6a'):
        return None

    rest = script_hex[2:]
    if len(rest) < 2:
        return None

    try:
        push_len = int(rest[0:2], 16)
    except ValueError:
        return None

    payload_hex_start = 2
    payload_hex_end = 2 + push_len * 2
    if len(rest) < payload_hex_end:
        return None

    payload_bytes = bytes.fromhex(rest[payload_hex_start:payload_hex_end])

    if len(payload_bytes) < 40:
        return None

    if payload_bytes[0] != 0x91:
        return None

    # Use exactly first 40 bytes
    payload = payload_bytes[:40]

    magic = payload[0]
    content_type = payload[1]
    block_height = int.from_bytes(payload[2:6], 'big')    # Big-endian
    asset_type = int.from_bytes(payload[6:8], 'big')      # Big-endian
    bet_data_raw = payload[8:40]

    # Parse 32 bytes as 16 little-endian uint16 values
    bet_data = []
    for i in range(0, 32, 2):
        val = int.from_bytes(bet_data_raw[i:i+2], 'little')
        bet_data.append(val)
    
    # Create bet dictionary mapping characters '0'-'f' to bet amounts
    bet_dict = {}
    hex_chars = '0123456789abcdef'
    for i, amount in enumerate(bet_data):
        if amount > 0:  # Only include non-zero bets
            bet_dict[hex_chars[i]] = amount

    return {
        "magic": magic,
        "content_type": content_type,
        "block_height": block_height,
        "asset_type": asset_type,
        "bet_data": bet_data,
        "bet_dict": bet_dict
    }

def main():
    print("🔍 BHASH OP_RETURN Parser")
    print("-" * 50)
    
    choice = input("Choose input method:\n[1] Enter txid\n[2] Paste raw transaction hex\n> ").strip()
    
    tx_hex = None
    if choice == '1':
        txid = input("\nEnter transaction ID (txid): ").strip()
        if not txid:
            print("❌ txid cannot be empty")
            return
        print(f"Fetching transaction from mempool.space...")
        tx_hex = fetch_tx_hex(txid)
        if not tx_hex:
            return
    elif choice == '2':
        tx_hex = input("\nEnter full transaction hex: ").strip()
        if not tx_hex:
            print("❌ Hex cannot be empty")
            return
    else:
        print("❌ Invalid choice")
        return

    print("\n✅ Parsing transaction outputs...")
    try:
        scripts = extract_vout_scripts(tx_hex)
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        return

    found = False
    for idx, script in enumerate(scripts):
        result = parse_bhash_from_script(script)
        if result:
            found = True
            print("\n" + "="*60)
            print(f"🎯 BHASH OP_RETURN found in output #{idx}")
            print("="*60)
            print(f"MAGIC_NUMBER : 0x{result['magic']:02x} (BHASH protocol)")
            print(f"CONTENT_TYPE : {result['content_type']} (0x{result['content_type']:02x})")
            print(f"BLOCK_HEIGHT : {result['block_height']}")
            asset_name = get_asset_type_name(result['asset_type'])
            print(f"ASSET_TYPE   : {asset_name}")
            print(f"BET_DATA     : {result['bet_data']}")
            
            # Display bet dictionary
            if result['bet_dict']:
                print(f"BET_DICT     : {result['bet_dict']}")
                total_bets = sum(result['bet_dict'].values())
                print(f"TOTAL BETS   : {total_bets} bets")
                print(f"BET DETAILS : {', '.join([f'{char}:{amount}' for char, amount in result['bet_dict'].items()])}")
            else:
                print(f"BET_DICT     : No bets")
                print(f"TOTAL BETS   : 0 bets")
            print("="*60)

    if not found:
        print("\n🔍 No BHASH OP_RETURN (MAGIC=0x91) found in this transaction.")

if __name__ == "__main__":
    main()