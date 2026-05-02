import hashlib
import json
import time
import uuid

from eth_account import Account
from eth_account.messages import encode_defunct


def _ensure_0x_prefix(hex_value: str) -> str:
    return hex_value if hex_value.startswith("0x") else f"0x{hex_value}"


def generate_did() -> str:
    return f"did:custom:{uuid.uuid4()}"


def create_ethereum_account() -> dict:
    account_data = create_new_ethereum_account()
    private_key_hex = account_data["privateKey"]
    public_key = account_data["address"]

    return {
        "privateKey": private_key_hex,
        "publicKey": public_key,
        "download": json.dumps(
            {
                "privateKey": private_key_hex,
                "publicKey": public_key,
            },
            indent=2,
        ),
    }


def generate_nonce() -> str:
    seed = f"{uuid.uuid4()}:{time.time()}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def create_new_ethereum_account() -> dict:
    """
    Create a fresh Ethereum account.
    """
    account = Account.create()
    return {
        "address": account.address,
        "privateKey": _ensure_0x_prefix(account.key.hex()),
    }


def sign_message_with_private_key(message: str, private_key: str) -> str:
    """
    Sign a UTF-8 message using an Ethereum private key.
    """
    encoded_message = encode_defunct(text=message)
    signed_message = Account.sign_message(encoded_message, private_key=private_key)
    return signed_message.signature.hex()


def recover_signer_address(message: str, signature: str) -> str:
    """
    Recover the signer Ethereum address from message + signature.
    """
    encoded_message = encode_defunct(text=message)
    return Account.recover_message(encoded_message, signature=signature)


if __name__ == "__main__":
    # Example usage
    wallet = create_new_ethereum_account()
    sample_message = "Hello from DID authentication"
    sample_signature = sign_message_with_private_key(sample_message, wallet["privateKey"])
    recovered_address = recover_signer_address(sample_message, sample_signature)

    print("Address:", wallet["address"])
    print("Private Key:", wallet["privateKey"])
    print("Signature:", sample_signature)
    print("Recovered Address:", recovered_address)
    print("Valid Signature:", recovered_address.lower() == wallet["address"].lower())
