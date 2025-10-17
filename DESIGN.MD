# BHASH Technical Implementation Documentation

## System Architecture Overview

The BHASH platform is built on the Bitcoin blockchain, implementing betting data storage on-chain through OP_RETURN, ensuring system transparency and immutability.

### Core Workflow

1. **User Betting**: Users place bets through wallets that support OP_RETURN
2. **Data On-Chain**: Betting data is recorded on the Bitcoin blockchain through OP_RETURN
3. **Automatic Drawing**: Drawing is conducted based on the last character of the block hash
4. **Prize Distribution**: Automatically calculate and distribute prizes to winners
5. **Token Distribution**: Simultaneously distribute BHASH tokens

---

## Wallet and Transaction Support

### Wallet Plugin Requirements

Users need to use wallets that support custom OP_RETURN. When transferring to the **current betting address**, they must **simultaneously attach an OP_RETURN output** containing the 16-character betting distribution encoded according to the protocol.

### Transaction Structure

Each betting transaction contains:
- **Output 1**: Amount → Current betting address (for fund aggregation)
- **Output 2**: OP_RETURN → Encoded betting data (40 bytes)

> ⚠️ If users do not include OP_RETURN, it is considered an invalid bet, and funds can be set for automatic refund or platform collection (rules must be announced in advance).

---

## Automatic Processing Flow

### Step 1: Determine Betting Deadline and Filter Invalid Transactions

- Betting deadline is the **timestamp of the current block's parent block** (i.e., the previous block's mining time)
- Scan all incoming transactions to the current betting address, **filter out transactions with timestamp ≥ current block time** (i.e., "late bets" or "delayed confirmation" transactions), add them to the **refund queue** for subsequent refund (need to record TXID + output index)

### Step 2: Capture Valid Betting Transactions and Parse

- Get all **confirmed before deadline** incoming transactions
- For each transaction:
  - Extract **incoming amount** (output value to betting address)
  - Find its **OP_RETURN output**, decode to get 16-character betting distribution (e.g., `'a':100, '9':15`)
  - According to encoding rules, **calculate the total bet count declared in this OP_RETURN** (sum of all character bet counts)
  - Verify **asset type** (2 bytes) matches betting rules

### Step 3: Amount Consistency Verification (Critical Risk Control)

- Compare: **Actual incoming transaction amount (sats)** vs **Total bet count declared in OP_RETURN × Unit bet value (sats/bet)**
- If equal → Consider as valid bet, accumulate to global betting pool
- If not equal → **Mark as abnormal transaction**, pause current drawing, notify operations for manual verification (prevent data tampering or wallet bugs)

> ✅ Recommendation: Fixed unit bet value (e.g., 1 bet = 1000 sats), clearly prompt users on frontend

### Step 4: Platform Commission (10%)

- Calculate total valid betting amount for current period `Total`
- Automatically construct transaction, send `0.1 × Total` to **platform cold wallet** (can be delayed for batch processing to reduce fees)
- Remaining `0.9 × Total` as **distributable prize pool**

### Step 5: Drawing and Prize Distribution

- Get current block's **block hash**, take **lower 4 bits of hash's last byte** → corresponds to a 0–f character
- Query all valid bets, **total bet count for that character** `WinningBets`
- If `WinningBets > 0`:
  - Distribute prizes proportionally: each winner gets `(their bet count / WinningBets) × Prize pool`
  - Automatically construct multi-output transaction, send payments to winning addresses (can be batched)
- If `WinningBets == 0` (no one won):
  - Roll **entire prize pool** into **next period prize pool** (need to accumulate in next period drawing logic)

---

## Key Security and Engineering Recommendations

1. **Address Isolation**: Use **fresh, one-time betting addresses** for each period (derived from platform HD wallet), avoid historical data confusion
2. **Transaction Confirmations**: Wait for block confirmations before drawing (e.g., 6 confirmations), prevent reorganization causing betting state changes
3. **OP_RETURN Mandatory Verification**: Transactions without OP_RETURN are considered invalid and do not participate in drawing
4. **Refund Mechanism**: For invalid/timeout transactions, need to record input UTXO, construct refund transactions (note fee source)
5. **Logging and Auditing**: Complete record of each period's TXID, amounts, OP_RETURN, verification results, distribution details for public verification
6. **Anti-Sybil Attack**: Can combine address behavior analysis, but on-chain games typically accept multi-address betting

---

## Summary

This solution uses **OP_RETURN as a trusted data carrier**, ensuring betting authenticity through "amount + metadata dual verification", combining block timestamps to achieve automatic deadlines, utilizing fixed encoding structure for efficient parsing of 16-way betting, supporting 65,536 asset types, ultimately achieving **automatic drawing, automatic prize distribution, automatic rollover** closed loop. The entire process requires no additional user operations, the platform only needs to maintain monitoring services and signing private keys, balancing decentralization spirit with operational efficiency.

---

## OP_RETURN Data Flow

The following is a detailed description of the **complete write and read process of OP_RETURN data in Bitcoin on-chain betting systems**, covering key aspects such as user side, on-chain structure, node propagation, backend parsing, etc.

## BHASH Protocol Specification

### Magic Number

**BHASH_MAGIC_NUMBER = 0x91**

This magic number is used to identify BHASH protocol data, ensuring only OP_RETURN conforming to this protocol format will be recognized and processed. Choosing 0x91 is to distinguish it from other protocols.

### Content Type

**CONTENT_TYPE_BHASH_BET = txscript.OP_DATA_1 = 0x01**

Used to identify betting type data content.

### Data Format Structure

Complete OP_RETURN script format:
```
OP_RETURN (0x6a) + MAGIC_NUMBER (0x91) + CONTENT_TYPE (0x01) + DATA
```

Where DATA part is 39 bytes long, total OP_RETURN data length is 41 bytes (1 + 1 + 1 + 38).

The DATA part structure is:
```[1B content type][4B block height][2B asset type][2B bet count for '0'][2B for '1']...[2B for 'f']```

Total data length: 1 + 4 + 2 + 32 = 39 bytes

### Detailed Data Structure

Complete OP_RETURN data structure:

| Byte Position | Field Name      | Size | Value | Description
|---------------|-----------------|------|-------|------------------|
| 0              | OP_RETURN       | 1B   | 0x6a  | OP_RETURN opcode
| 1              | MAGIC_NUMBER    | 1B   | 0x91  | BHASH protocol identifier
| 2              | CONTENT_TYPE    | 1B   | 0x01  | Content type identifier
| 3-6            | BLOCK_HEIGHT    | 4B   | -     | Target block height
| 7-8            | ASSET_TYPE       | 2B   | -     | Asset type (extension)
| 9-40           | BET_DATA         | 32B  | -     | 16-character betting data

**Total Length**: 41 bytes (1 + 1 + 1 + 4 + 2 + 32)

### Asset Type Definitions

The asset type field (2 bytes) is used to identify the asset type used for betting:

- **0x0000 (0)**: Bitcoin (BTC) - Default asset type
- **0x0001 (1)**: Bitcoin-Satoshi Network (BTC-SATS) - Bitcoin's smallest unit
- **0x0002 (2)**: BHASH - BHASH protocol dedicated asset type
- **0x0003-0xFFFF**: Reserved extensions - Reserved for future possible asset types (65,533 available values)

### Asset Type Extension Advantages

#### Capacity Comparison
- **1-byte version**: Supports 256 asset types (0x00-0xFF)
- **2-byte version**: Supports 65,536 asset types (0x0000-0xFFFF)
- **Extension multiplier**: 256x capacity increase

#### Currently Supported Asset Types
```typescript
// Currently supported asset types (simplified version)
const assetCategories = {
  // Core asset types
  0x0000: 'BTC',        // Bitcoin - Default asset type
  0x0001: 'BTC_SATS',   // Bitcoin-Satoshi Network - Bitcoin's smallest unit
  0x0002: 'BHASH',      // BHASH - BHASH protocol dedicated asset type
  
  // Reserved extensions (0x0003-0xFFFF: 65,533 available values)
  // More asset types can be added in the future as needed
};
```

### Usage Examples

```go
// Create Bitcoin betting data
betData := []byte{
    // 4-byte block height (big-endian)
    0x00, 0x00, 0x12, 0x34, // Block height 4660
    // 2-byte asset type (big-endian)
    0x00, 0x00, // Bitcoin (0x0000)
    // 32-byte betting distribution (16 characters, each 2 bytes little-endian)
    0x00, 0x64, // '0': 100 bets
    0x00, 0x00, // '1': 0 bets
    // ... bet counts for other characters
}

// Create Bitcoin-Satoshi Network betting data
betData := []byte{
    // 4-byte block height (big-endian)
    0x00, 0x00, 0x12, 0x34, // Block height 4660
    // 2-byte asset type (big-endian)
    0x00, 0x01, // Bitcoin-Satoshi Network (0x0001)
    // 32-byte betting distribution
    0x00, 0x64, // '0': 100 bets
    // ... bet counts for other characters
}

// Create BHASH betting data
betData := []byte{
    // 4-byte block height (big-endian)
    0x00, 0x00, 0x12, 0x34, // Block height 4660
    // 2-byte asset type (big-endian)
    0x00, 0x02, // BHASH (0x0002)
    // 32-byte betting distribution
    0x00, 0x64, // '0': 100 bets
    // ... bet counts for other characters
}
```

---

### I. OP_RETURN Data Write Process (User → On-Chain)

#### 1. **User Operation**
- User selects betting characters on frontend (e.g., `'a': 100 bets, '9': 15 bets`).
- Frontend calculates transfer amount based on current period rules (e.g., 1 bet = 1000 sats):  
  `(100 + 15) × 1000 = 115,000 sats`.
- Frontend calls OP_RETURN supporting wallet plugin (sat20wallet), constructs a transaction with three outputs:
  - **Output 1**: Amount `115,000 sats` → Send to current period's **unique betting address** (e.g., `bc1q...`).
  - **Output 2**: `OP_RETURN` → Payload is 39-byte data encoded according to protocol (1 byte content type + 4 bytes block height + 2 bytes asset type + 16×2 bytes betting distribution).
  - **Output 3**: Change amount → Send back to user's own address (remaining amount after deducting betting amount and miner fees).

#### 2. **Transaction Construction Details**
- **Betting Output**: Standard P2WPKH or P2PKH output, amount is total betting amount
- **OP_RETURN Output**:  
  `OP_RETURN <39-byte-payload>`  
  Where payload strictly follows predefined binary format (e.g., 1 byte content type, block height big-endian, asset type 2 bytes big-endian, betting array little-endian uint16)
- **Change Output**: Standard P2WPKH or P2PKH output, amount is `total input amount - betting amount - miner fee`
- Transaction needs to pay sufficient miner fees to ensure timely confirmation
- Wallet signs transaction and broadcasts to Bitcoin network

#### 3. **On-Chain Write**
- Bitcoin nodes receive transaction, verify its format, signature, OP_RETURN length (≤80 bytes).
- If compliant with standards (e.g., Bitcoin Core default policy), transaction enters mempool.
- Miners package transaction into block, OP_RETURN data **permanently written to blockchain**, becoming immutable part of transaction.
- Note: OP_RETURN output **does not create UTXO**, does not pollute unspent output set.

---

### II. OP_RETURN Data Read Process (On-Chain → Backend System)

#### 1. **Trigger Timing**
- Backend monitors Bitcoin nodes (e.g., through `bitcoind` ZMQ or RPC).
- When **new block is confirmed** (e.g., ≥1 confirmation), system starts current period drawing process.

#### 2. **Locate Related Transactions**
- Based on current period's **betting address**, call `listunspent` or scan block transactions, get all **transactions incoming to this address**.
- For each transaction:
  - Get its **confirmation timestamp** (usually block time where it's located).
  - If timestamp ≥ current period deadline (i.e., parent block time), mark as **invalid/timeout**, enter refund process.
  - Otherwise, consider as **valid betting transaction**, enter parsing stage.

#### 3. **Parse OP_RETURN Payload**
- Traverse all outputs of transaction, find `scriptPubKey` starting with `6a` (OP_RETURN opcode).
- Extract subsequent data payload (`pushdata` content).
- Verify payload length is 39 bytes (or protocol-defined length).
- Decode according to protocol:
  - Byte 1 → Content type (0x01), used to identify betting type.
  - Bytes 2-5 → Block height (big-endian converted to integer), **verify if equals current period target height** (prevent wrong betting).
  - Bytes 6-7 → Asset type (2 bytes big-endian), used to identify betting asset type (e.g., 0x0000=Bitcoin, 0x0002=Ethereum, etc.).
  - Bytes 8-39 → Every 2 bytes as a group, total 16 groups, each group little-endian converted to uint16, corresponding to bet counts for characters `'0'` to `'f'`.
- Rebuild betting dictionary: e.g., `{ 'a': 100, '9': 15, ... }`.

#### 4. **Data Verification and Integration**
- Calculate **total bet count** in OP_RETURN: `sum(all character bet counts)`.
- Calculate **should transfer amount**: `total bet count × unit bet value (sats)`.
- Compare with actual incoming transaction amount:
  - Equal → Accept bet, accumulate to global pool.
  - Not equal → Mark as abnormal, alert and pause automatic process.

#### 5. **Subsequent Processing**
- After all valid OP_RETURN data parsing is complete, system has complete betting distribution.
- Combined with block hash last character, calculate winners and prize distribution.
- Finally generate drawing report, including each valid transaction's TXID, betting details, winning status, etc., for public auditing.

---

### III. Key Guarantee Mechanisms

- **Immutability**: Once OP_RETURN is on-chain, data is bound to transaction and cannot be modified.
- **Transparent Verification**: Anyone can view OP_RETURN content through block explorer and decode using public protocol.
- **Anti-Wrong Betting**: Through block height field, ensure users don't send bets to wrong periods.
- **Automatic Reconciliation**: Amount and data dual verification, eliminate false betting or wallet bug-caused fund risks.

---

### Summary

OP_RETURN serves as **on-chain structured metadata channel** in this system:  
**When writing**, users encode betting intentions into standard binary payload through wallet;  
**When reading**, backend precisely locates, parses, verifies, restoring complete business semantics.  
The entire process relies on Bitcoin's underlying security, achieving "fund + intention" dual on-chain, providing trusted, automatic, transparent infrastructure for decentralized games.