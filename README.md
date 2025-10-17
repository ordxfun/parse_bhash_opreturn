# BHASH OP_RETURN Parser

A Python tool for parsing BHASH protocol OP_RETURN data from Bitcoin transactions.

## Features

- Parse BHASH OP_RETURN data from Bitcoin transactions
- Support for both transaction ID input and raw hex input
- Extract bet data with character-to-bet-amount mapping
- Display asset type information with human-readable names
- Support for SegWit transactions

> 📄 **[Complete protocol and design documentation see DESIGN.MD](./DESIGN.MD)**


## Usage

### 🧪 Example Run

```bash
$ python3 parse_bhash_opreturn.py
Choose input method:
[1] Enter txid
[2] Paste raw transaction hex
> 1

Enter transaction ID (txid): a0f2d40c6878995c10b10ec9a64effbb15fc6dafbb04593d32872c9e3a6bd52f
```

**Output Example:**
```
============================================================
🎯 BHASH OP_RETURN found in output #0
============================================================
MAGIC_NUMBER : 0x91 (BHASH protocol)
CONTENT_TYPE : 1 (0x01)
BLOCK_HEIGHT : 919326
ASSET_TYPE   : BTC (Bitcoin)
BET_DATA     : [100, 0, 0, 0, 0, 0, 0, 0, 0, 0, 15, 0, 0, 0, 0, 0]
BET_DICT     : {'0': 100, 'a': 15}
TOTAL BETS   : 115 bets
BET DETAILS : 0:100, a:15
============================================================
```

## BHASH Protocol Format

The BHASH OP_RETURN follows this structure:
- **Magic Number**: 0x91 (BHASH protocol identifier)
- **Content Type**: Protocol content type
- **Block Height**: Target block height (4 bytes, big-endian)
- **Asset Type**: Asset type identifier (2 bytes, big-endian)
- **Bet Data**: 32 bytes parsed as 16 uint16 values (little-endian)

### Asset Types

- `0x0000`: BTC (Bitcoin)
- `0x0001`: BTC (Bitcoin - Satoshinet)
- `0x0002`: BHASH (BHASH Protocol Asset Type)
- `0x0003-0xFFFF`: Reserved Extensions

### Bet Data Format

The 32-byte bet data is parsed as 16 groups of 2 bytes each, converted from little-endian to uint16 values. Each value represents the bet amount for the corresponding hex character:

- Position 0 → Character '0'
- Position 1 → Character '1'
- ...
- Position 10 → Character 'a'
- ...
- Position 15 → Character 'f'

Only non-zero bet amounts are included in the bet dictionary.

## Requirements

- Python 3.6+
- Internet connection (for fetching transactions from mempool.space)

## Installation

No additional dependencies required. Uses only Python standard library.

```bash
git clone <repository-url>
cd parse_bhash_opreturn
python3 parse_bhash_opreturn.py
```

> Note: Based on the hex example `6a289101000e071e...`, BLOCK_HEIGHT is `00 0e 07 1e` = 919,326