# DecentraBlog

Minimal decentralized blog with DID-based identity and signed posts.

## What it does

- Generate an Ethereum-style DID (`did:eth:0x...`)
- Register DID on-chain
- Publish signed blog posts
- Verify post signatures

## Stack

- Frontend: `frontend/index.html` (vanilla HTML/CSS/JS)
- Backend: Flask API (`backend`)
- Blockchain: Hardhat local node + Solidity contracts
- DB: SQLite (`backend/decentrablog.db`)

## Prerequisites

- Node.js 16+
- Python 3.8+

## Quick Start

Open 3 terminals from project root.

### 1) Install dependencies

```bash
npm install
cd backend
pip install -r requirements.txt
cd ..
```

### 2) Start blockchain node (Terminal 1)

```bash
npx hardhat node
```

### 3) Configure env + deploy contracts (Terminal 2)

```bash
cd backend
cp .env.example .env
# Add DEPLOYER_PRIVATE_KEY from hardhat node output
cd ..
python scripts/deploy.py
```

### 4) Start backend API (Terminal 2)

```bash
cd backend
python app.py
```

### 5) Start frontend (Terminal 3)

```bash
cd frontend
python -m http.server 5500
```

Open: `http://localhost:5500`

## App Flow

1. Register DID from UI (keypair + DID generated).
2. DID is registered on-chain and saved in DB.
3. Compose and publish a post (signed with private key).
4. Backend verifies signature and stores post.
5. Reader verifies post integrity from UI.

## Useful Commands

```bash
# Run tests
cd backend
pytest tests/ -v

# Health check
curl http://localhost:5000/health

# List posts
curl http://localhost:5000/api/posts
```

