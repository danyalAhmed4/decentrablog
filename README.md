# Decentralized Identity (DID) Auth System

This project contains:

- A Solidity DID registry smart contract: `DIDRegistry.sol`
- A Flask backend for registration + authentication: `app.py`
- Blockchain interaction layer: `blockchain.py`
- Crypto helper utilities: `crypto.py`

## Tech Stack

- Solidity `^0.8.0`
- Python 3.10+
- Flask
- web3.py
- eth-account

## Project Structure

- `DIDRegistry.sol` - Smart contract for DID storage and lookup
- `app.py` - Flask API with `/register`, challenge request, verify, and identity lookup
- `blockchain.py` - Contract read/write functions via Web3
- `crypto.py` - DID generation, Ethereum account generation, nonce generation
- `requirements.txt` - Python dependencies

## 1) Deploy the Smart Contract

Deploy `DIDRegistry.sol` using your preferred tool (Hardhat/Remix/Foundry).

After deployment, keep these values:

- Contract address
- Contract ABI JSON

Save ABI JSON into the project root as:

- `DIDRegistry.abi.json`

## 2) Configure Environment Variables

Set these before running Flask:

- `RPC_URL` - Ethereum JSON-RPC URL (default in code: `http://127.0.0.1:8545`)
- `DID_CONTRACT_ADDRESS` - deployed DIDRegistry contract address
- `DID_CONTRACT_ABI_PATH` - ABI file path (default: `DIDRegistry.abi.json`)
- `RELAYER_PRIVATE_KEY` - private key of account used to send `registerIdentity` tx

PowerShell example:

```powershell
$env:RPC_URL="http://127.0.0.1:8545"
$env:DID_CONTRACT_ADDRESS="0xYourContractAddress"
$env:DID_CONTRACT_ABI_PATH="DIDRegistry.abi.json"
$env:RELAYER_PRIVATE_KEY="0xYourRelayerPrivateKey"
```

## 3) Install and Run Backend

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Flask runs on:

- `http://localhost:5000`

## 4) API Endpoints

### `POST /register`

Request body:

```json
{
  "name": "Alice",
  "email": "alice@example.com"
}
```

Response includes:

- `did`
- `publicKey`
- `privateKey` (with `0x` prefix)
- `privateKeyDownload` (JSON string containing `did`, `privateKey`, `publicKey`)
- `txHash`

---

### `POST /auth/request-challenge`

Request body:

```json
{
  "did": "did:custom:uuid-value",
  "appId": "my-dapp"
}
```

Response:

- `message`
- `nonce`

Nonce validity is 2 minutes and stored in memory.

---

### `POST /auth/verify`

Request body:

```json
{
  "did": "did:custom:uuid-value",
  "message": "Login to my-dapp at 1714671000 with nonce ...",
  "signature": "0x...",
  "nonce": "abc123...",
  "appId": "my-dapp"
}
```

Response:

- `verified: true/false`
- `name` (only when verified)

---

### `GET /identity/<did>`

Example:

`GET /identity/did:custom:uuid-value`

Returns identity data from blockchain:

- `did`
- `name`
- `email`
- `publicKey`

## 5) Minimal Frontend (HTML/CSS/JS)

A simple no-framework frontend is available in `static/`:

- `static/index.html`
- `static/register.html`
- `static/sign-verify.html`
- `static/register.js`
- `static/sign-verify.js`
- `static/styles.css`

After running `python app.py`, open:

- `http://localhost:5000/static/index.html`

### Register Page

- Enter `name` + `email`
- Click **Register**
- Calls `POST /register`
- Shows DID + public key
- Automatically downloads private key JSON file
- Duplicate `name + email` registrations are blocked on-chain (HTTP `409` from backend)

### Sign & Verify Page

- Enter `did` and paste `private key`
- Click **Sign & Verify**
- Calls `POST /auth/request-challenge`
- Signs the challenge message in browser using `ethers.js`
- Sends signed payload to `POST /auth/verify`
- Displays:
  - `Verified ✅` if valid
  - `Failed ❌` if invalid

Note: `sign-verify.html` uses CDN `ethers@6` for browser signing and a fixed internal app ID (`did-web`).

## Notes

- Nonces are kept in-memory (`nonce_store`), so they reset when the server restarts.
- Duplicate registration prevention is enforced by the smart contract using `name+email` hash.
- Private keys are returned only for demo/dev flow. In production, avoid returning raw keys.
- Keep `RELAYER_PRIVATE_KEY` secret and never commit it.

## Important After Contract Changes

If you modify `DIDRegistry.sol`, you must:

- redeploy the contract
- regenerate `DIDRegistry.abi.json`
- update `DID_CONTRACT_ADDRESS` to the new deployed address

## 6) Separate Blog App (DID Login + SQLite)

A separate blog app now exists in `blog/` with its own backend and frontend:

- `blog/app.py` - Flask app for blog auth/session/posts
- `blog/blog.db` - SQLite database (auto-created)
- `blog/static/` - plain HTML/CSS/JavaScript frontend

### Blog Features

- DID login flow via challenge + signature verification
- Browser signing with `ethers.js`
- Fixed app ID internally (`did-blog`) so users only enter DID + private key
- Session token stored in `localStorage`
- Logout support
- Blog posts persisted in SQLite

### Run Blog App

1. Start the DID backend first (`python app.py`) on port `5000`
2. In a new terminal, run blog app:

```powershell
cd blog
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DID_API_BASE="http://127.0.0.1:5000"
python app.py
```

Open:

- `http://127.0.0.1:5001`

## Reusable `eth_account` Functions

`crypto.py` now includes reusable helpers for:

- creating a new Ethereum account
- signing a message with a private key
- recovering signer address from message + signature

Functions:

- `create_new_ethereum_account()`
- `sign_message_with_private_key(message, private_key)`
- `recover_signer_address(message, signature)`

Example usage:

```python
from crypto import (
    create_new_ethereum_account,
    recover_signer_address,
    sign_message_with_private_key,
)

wallet = create_new_ethereum_account()
message = "Hello from DID authentication"
signature = sign_message_with_private_key(message, wallet["privateKey"])
recovered = recover_signer_address(message, signature)

print(wallet["address"])
print(signature)
print(recovered)
print(recovered.lower() == wallet["address"].lower())
```

You can also run `python crypto.py` to execute the built-in example.

## Ongoing Updates

This README is now the living runbook for the project. As we add features, we will keep this file updated with:

- new setup steps
- new endpoints
- config changes
- testing instructions
