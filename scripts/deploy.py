"""
Deployment script for smart contracts using web3.py
Compiles and deploys DIDRegistry and BlogRegistry contracts
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Optional
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from dotenv import load_dotenv, set_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ENV_FILE = PROJECT_ROOT / "backend" / ".env"
ROOT_ENV_FILE = PROJECT_ROOT / ".env"


def load_environment() -> None:
    """Load environment variables with a deterministic search order."""
    # Prefer backend/.env since this is where project instructions store runtime config.
    if BACKEND_ENV_FILE.exists():
        load_dotenv(dotenv_path=BACKEND_ENV_FILE, override=True)
        return

    # Fallback to project root .env if present.
    if ROOT_ENV_FILE.exists():
        load_dotenv(dotenv_path=ROOT_ENV_FILE, override=True)
        return

    # Last-resort behavior: keep existing environment-only configuration.
    load_dotenv(override=True)


def load_abi_and_bytecode(contract_name: str) -> tuple:
    """Load ABI and bytecode from compiled contract artifacts"""
    try:
        # Try to load from artifacts directory (Hardhat output)
        artifact_path = Path(__file__).parent.parent / "artifacts" / "contracts" / f"{contract_name}.sol" / f"{contract_name}.json"
        if artifact_path.exists():
            with open(artifact_path) as f:
                artifact = json.load(f)
                return artifact["abi"], artifact["bytecode"]
    except:
        pass
    
    print(f"Warning: Could not load artifacts for {contract_name}")
    return None, None


def deploy_contract(
    w3: Web3,
    account: LocalAccount,
    contract_name: str,
    constructor_args: Optional[list[Any]] = None,
) -> Optional[str]:
    """Deploy a contract and return its address"""
    print(f"\n📦 Deploying {contract_name}...")
    
    abi, bytecode = load_abi_and_bytecode(contract_name)
    if not abi or not bytecode:
        print(f"❌ Failed to load {contract_name} artifacts")
        return None
    
    # Create contract factory
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Build transaction
    if constructor_args:
        tx = Contract.constructor(*constructor_args).build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 3000000,
            "gasPrice": w3.eth.gas_price,
        })
    else:
        tx = Contract.constructor().build_transaction({
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 3000000,
            "gasPrice": w3.eth.gas_price,
        })
    
    # Sign and send transaction
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print(f"   Transaction hash: {tx_hash.hex()}")
    print(f"   Waiting for confirmation...")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    contract_address = receipt["contractAddress"]
    if not contract_address:
        print(f"❌ {contract_name} deployment receipt missing contractAddress")
        return None
    print(f"   ✓ {contract_name} deployed at: {contract_address}")
    print(f"   Block: {receipt['blockNumber']}")
    print(f"   Gas used: {receipt['gasUsed']}")
    
    return contract_address


def main():
    """Main deployment function"""
    print("🚀 DecentraBlog Smart Contract Deployment")
    print("=" * 50)
    load_environment()
    
    # Load environment
    provider_uri = os.getenv("WEB3_PROVIDER_URI", "http://127.0.0.1:8545")
    deployer_key = os.getenv("DEPLOYER_PRIVATE_KEY")
    
    if not deployer_key:
        print("❌ DEPLOYER_PRIVATE_KEY not set in .env")
        print(f"   Checked: {BACKEND_ENV_FILE}")
        print(f"   Fallback: {ROOT_ENV_FILE}")
        sys.exit(1)
    
    # Connect to blockchain
    w3 = Web3(Web3.HTTPProvider(provider_uri))
    if not w3.is_connected():
        print(f"❌ Cannot connect to {provider_uri}")
        sys.exit(1)
    
    print(f"✓ Connected to {provider_uri}")
    print(f"  Chain ID: {w3.eth.chain_id}")
    
    # Get deployer account
    deployer = Account.from_key(deployer_key)
    balance = w3.eth.get_balance(deployer.address)
    print(f"✓ Deployer: {deployer.address}")
    print(f"  Balance: {w3.from_wei(balance, 'ether')} ETH")
    
    # Deploy DIDRegistry
    did_registry_address = deploy_contract(w3, deployer, "DIDRegistry")
    if not did_registry_address:
        sys.exit(1)
    
    # Deploy BlogRegistry with DIDRegistry address
    blog_registry_address = deploy_contract(
        w3, deployer, "BlogRegistry", 
        constructor_args=[did_registry_address]
    )
    if not blog_registry_address:
        sys.exit(1)
    
    # Save addresses to backend/.env
    env_file = Path(__file__).parent.parent / "backend" / ".env"
    set_key(env_file, "DID_REGISTRY_ADDRESS", did_registry_address)
    set_key(env_file, "BLOG_REGISTRY_ADDRESS", blog_registry_address)
    set_key(env_file, "BLOCKCHAIN_ENABLED", "true")
    
    print("\n" + "=" * 50)
    print("✓ Deployment Successful!")
    print("\nContract Addresses:")
    print(f"  DIDRegistry:  {did_registry_address}")
    print(f"  BlogRegistry: {blog_registry_address}")
    print(f"\nSaved to: {env_file}")
    print("\nNext steps:")
    print("  1. Copy .env.example to .env in backend/")
    print("  2. Update WEB3_PROVIDER_URI and DEPLOYER_PRIVATE_KEY")
    print("  3. Run: cd backend && python app.py")


if __name__ == "__main__":
    main()
