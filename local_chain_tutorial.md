# Local Chain Tutorial — Ganache + Remix

A step-by-step guide to deploying and interacting with smart contracts locally using Ganache and Remix.

---

## 1. Download & Install Ganache

- Go to: https://archive.trufflesuite.com/ganache/
- Download version **2.7.1** for your OS (Windows/Mac/Linux)
- Install and open it

---

## 2. Start a Local Blockchain

1. Open Ganache
2. Click **"Quickstart Ethereum"**
3. Ganache will automatically start a local blockchain with 10 funded test accounts

---

## 3. Get Your RPC URL

At the top of the Ganache window you will see:

```
RPC SERVER: HTTP://127.0.0.1:7545
```

This is your `RPC_URL`. Use it in your `.env` file:

```
RPC_URL=http://127.0.0.1:7545
```

---

## 4. Get Your Private Key

1. In Ganache, you will see 10 accounts listed
2. Click the **🔑 key icon** on the right of any account
3. Copy the private key shown

Use it in your `.env` file:

```
RELAYER_PRIVATE_KEY=<your copied private key>
```

---

## 5. Configure Remix Compiler Settings

Ganache 2.7.1 supports up to the **London** EVM. Mismatched settings will cause deployment to fail.

1. Go to the **Solidity Compiler** tab in Remix
2. Set **Compiler version** to `0.8.17` or lower
3. Expand **"Advanced Configurations"**
4. Set **EVM Version** to `london`
5. Click **Compile DIDRegistry.sol**

> ⚠️ Also check the top of your `.sol` file. If the pragma line says `^0.8.20` or higher, change it to:
> ```solidity
> pragma solidity ^0.8.17;
> ```

---

## 6. Connect Remix to Ganache

1. In Remix, go to the **Deploy tab**
2. Change **Environment** to **"Custom - External HTTP Provider"**
3. Enter: `http://127.0.0.1:7545`
4. Remix will now show your Ganache accounts in the Account dropdown

---

## 7. Deploy Your Contract

1. Make sure `DIDRegistry.sol` is compiled with no errors
2. In the **Deploy tab**, click **Deploy**
3. Check Ganache's **Transactions tab** for the new contract address
4. Copy the contract address

Use it in your `.env` file:

```
DID_CONTRACT_ADDRESS=<your deployed contract address>
```

---

## 8. Export the ABI

1. After compiling in Remix, go to the **Solidity Compiler** tab
2. Click **"ABI"** copy button at the bottom
3. Paste it into a file called `DIDRegistry.abi.json` in your project root

Use it in your `.env` file:

```
DID_CONTRACT_ABI_PATH=DIDRegistry.abi.json
```

---

## 9. Full .env Example

```
RPC_URL=http://127.0.0.1:7545
DID_CONTRACT_ADDRESS=<deployed contract address from Ganache>
DID_CONTRACT_ABI_PATH=DIDRegistry.abi.json
RELAYER_PRIVATE_KEY=<private key from Ganache account>
```

---

## 10. Redeploying After Contract Changes

If you modify your contract, follow these steps:

1. In Remix → **Solidity Compiler** tab → click **Compile DIDRegistry.sol**
2. In Remix → **Deploy tab** → click **Deploy**
3. Get the **new contract address** from Ganache's Transactions tab
4. Update `DID_CONTRACT_ADDRESS` in your `.env` file
5. Re-export the ABI and replace `DIDRegistry.abi.json`

> ℹ️ You do **not** need to restart Ganache. The old contract still exists on the blockchain, you simply stop using it and point to the new one.

---

## Key Concepts

| Type | Gas Cost | Recorded on Chain | Example |
|------|----------|-------------------|---------|
| Transaction (Write) | Yes | ✅ Yes | Deploy contract, store data |
| Call (Read) | No | ❌ No | Read a `view` function |

- **Ganache Transactions tab** is the source of truth for all on-chain activity
- **Remix terminal** only shows transactions initiated from Remix in the current session — this is normal

---

## Troubleshooting

| Problem | Fix |
|--------|-----|
| Gas estimation failed on deploy | Check EVM version — set to `london` in Remix compiler |
| Remix doesn't show transactions | Check Ganache Transactions tab instead — this is normal |
| Wrong contract address | Always copy fresh address from Ganache after each deployment |
| Deployment rejected | Check pragma version in `.sol` file — must match compiler version |
