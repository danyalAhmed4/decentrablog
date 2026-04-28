"""
Cryptographic utilities for DID and post signing
Uses eth-keys, eth-account, and web3.py
"""

import secrets
from eth_keys.main import KeyAPI
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3


# Initialize key API with the active backend in this environment
key_api = KeyAPI()


def generate_keypair() -> dict:
    """
    Generate a new secp256k1 keypair
    
    Returns:
        dict: {
            "private_key": "0x<64 hex chars>",
            "public_key": "0x04<128 hex chars>",  # uncompressed
            "address": "0x<40 hex chars>",         # checksummed
            "did": "did:eth:0x<40 hex chars>"
        }
    """
    # Generate random private key
    private_key_bytes = secrets.token_bytes(32)
    private_key = key_api.PrivateKey(private_key_bytes)
    
    # Get public key (uncompressed format)
    public_key = private_key.public_key
    public_key_hex = "0x04" + public_key.to_hex()[2:]  # uncompressed format
    
    # Derive Ethereum address
    account = Account.from_key(private_key_bytes)
    address = Web3.to_checksum_address(account.address)
    
    return {
        "private_key": "0x" + private_key_bytes.hex(),
        "public_key": public_key_hex,
        "address": address,
        "did": f"did:eth:{address}"
    }


def sign_message(message: str, private_key_hex: str) -> dict:
    """
    Sign a message with Ethereum signed message format
    
    Args:
        message: The message to sign
        private_key_hex: Private key in hex format "0x<64 hex chars>"
    
    Returns:
        dict: {
            "message": message,
            "message_hash": "0x...",
            "signature": "0x<130 hex chars>",  # r+s+v
            "r": "0x...",
            "s": "0x...",
            "v": 27 or 28
        }
    """
    # Create account from private key
    account = Account.from_key(private_key_hex)
    
    # Create message hash using Ethereum signed message format
    message_hash = encode_defunct(text=message)
    
    # Sign the message
    signed_message = account.sign_message(message_hash)
    message_hash_bytes = signed_message.message_hash
    
    return {
        "message": message,
        "message_hash": Web3.to_hex(message_hash_bytes),
        "signature": signed_message.signature.hex(),
        "r": Web3.to_hex(signed_message.r),
        "s": Web3.to_hex(signed_message.s),
        "v": signed_message.v
    }


def verify_signature(message: str, signature_hex: str, expected_address: str) -> dict:
    """
    Verify a message signature and recover the signer address
    
    Args:
        message: The original message
        signature_hex: The signature in hex format "0x<130 hex chars>"
        expected_address: The expected signer address
    
    Returns:
        dict: {
            "valid": True/False,
            "recovered_address": "0x...",
            "expected_address": "0x...",
            "match": True/False
        }
    """
    try:
        # Create message hash using Ethereum signed message format
        message_hash = encode_defunct(text=message)
        
        # Recover the signer
        recovered_address = Account.recover_message(message_hash, signature=signature_hex)
        recovered_address = Web3.to_checksum_address(recovered_address)
        expected_address = Web3.to_checksum_address(expected_address)
        
        match = recovered_address.lower() == expected_address.lower()
        
        return {
            "valid": True,
            "recovered_address": recovered_address,
            "expected_address": expected_address,
            "match": match
        }
    except (ValueError, Exception) as e:
        return {
            "valid": False,
            "recovered_address": None,
            "expected_address": Web3.to_checksum_address(expected_address),
            "match": False,
            "error": str(e)
        }


def hash_content(title: str, body: str) -> str:
    """
    Hash content (title + body) using keccak256
    
    Args:
        title: Post title
        body: Post body
    
    Returns:
        str: keccak256 hash as "0x<64 hex chars>"
    """
    content = f"{title}:{body}"
    hash_obj = Web3.keccak(text=content)
    return Web3.to_hex(hash_obj)


def create_did_document(address: str, public_key: str, 
                       service_endpoint: str = "") -> dict:
    """
    Create a W3C-compliant DID document
    
    Args:
        address: Ethereum address
        public_key: Secp256k1 public key in hex format
        service_endpoint: Optional service endpoint URL
    
    Returns:
        dict: W3C DID document
    """
    checksum_address = Web3.to_checksum_address(address)
    did = f"did:eth:{checksum_address}"
    
    if not service_endpoint:
        service_endpoint = f"https://decentrablog.io/author/{checksum_address}"
    
    return {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "verificationMethod": [
            {
                "id": f"{did}#key-1",
                "type": "EcdsaSecp256k1VerificationKey2019",
                "controller": did,
                "publicKeyHex": public_key
            }
        ],
        "authentication": [f"{did}#key-1"],
        "service": [
            {
                "id": f"{did}#blog",
                "type": "BlogService",
                "serviceEndpoint": service_endpoint
            }
        ]
    }


def verify_content_hash(title: str, body: str, expected_hash: str) -> bool:
    """
    Verify that a content hash matches title and body
    
    Args:
        title: Post title
        body: Post body
        expected_hash: Expected hash in hex format
    
    Returns:
        bool: True if hash matches
    """
    computed_hash = hash_content(title, body)
    return computed_hash.lower() == expected_hash.lower()


def bytes32_from_hex(hex_str: str) -> bytes:
    """
    Convert hex string to bytes32
    
    Args:
        hex_str: Hex string (with or without 0x prefix)
    
    Returns:
        bytes: 32 bytes
    """
    if hex_str.startswith("0x"):
        hex_str = hex_str[2:]
    return bytes.fromhex(hex_str)
