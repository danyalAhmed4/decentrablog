"""
Utility script to generate a new DID
Useful for testing and getting started
"""

import sys
import json
sys.path.insert(0, str(__file__.parent) + "/../backend")

from crypto_utils import generate_keypair, create_did_document


def main():
    print("🔐 DecentraBlog DID Generator")
    print("=" * 50)
    
    # Generate keypair
    print("\nGenerating secp256k1 keypair...")
    keypair = generate_keypair()
    
    print("\n✓ Keypair Generated:")
    print(f"  Private Key: {keypair['private_key']}")
    print(f"  Public Key:  {keypair['public_key']}")
    print(f"  Address:     {keypair['address']}")
    print(f"  DID:         {keypair['did']}")
    
    # Create DID document
    print("\nGenerating DID Document...")
    did_document = create_did_document(
        keypair['address'],
        keypair['public_key'],
        ""
    )
    
    print("\n✓ DID Document:")
    print(json.dumps(did_document, indent=2))
    
    print("\n" + "=" * 50)
    print("💾 Save your private key in a secure location!")
    print("⚠️  Never share your private key with anyone.")
    print("\nYou can now use these credentials to:")
    print("  1. Register your DID on DecentraBlog")
    print("  2. Sign and publish blog posts")
    print("  3. Prove ownership of content on-chain")


if __name__ == "__main__":
    main()
