"""
Tests for cryptographic utilities
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from crypto_utils import (
    generate_keypair,
    sign_message,
    verify_signature,
    hash_content,
    create_did_document,
    verify_content_hash
)


class TestKeypairGeneration:
    def test_generate_keypair_format(self):
        """Test that generated keypair has correct format"""
        keypair = generate_keypair()
        
        # Check address format (0x + 40 hex chars = 42 total)
        assert keypair["address"].startswith("0x")
        assert len(keypair["address"]) == 42
        
        # Check private key format
        assert keypair["private_key"].startswith("0x")
        assert len(keypair["private_key"]) == 66  # 0x + 64 hex chars
        
        # Check public key format (uncompressed: 0x04 + 128 hex chars)
        assert keypair["public_key"].startswith("0x04")
        assert len(keypair["public_key"]) == 132
        
        # Check DID format
        assert keypair["did"].startswith("did:eth:")
        assert keypair["address"] in keypair["did"]
    
    def test_generate_keypair_unique(self):
        """Test that two generated keypairs are different"""
        keypair1 = generate_keypair()
        keypair2 = generate_keypair()
        
        assert keypair1["private_key"] != keypair2["private_key"]
        assert keypair1["address"] != keypair2["address"]
        assert keypair1["did"] != keypair2["did"]
    
    def test_generate_keypair_consistency(self):
        """Test that keypair components are consistent"""
        keypair = generate_keypair()
        
        # Re-generate DID document to ensure address matches
        did_doc = create_did_document(keypair["address"], keypair["public_key"])
        assert keypair["address"] in did_doc["id"]


class TestMessageSigning:
    def test_sign_and_verify_valid(self):
        """Test that a signed message can be verified"""
        keypair = generate_keypair()
        message = "Hello, blockchain!"
        
        # Sign message
        signature_data = sign_message(message, keypair["private_key"])
        assert len(signature_data["signature"]) == 130  # 65-byte signature in hex
        
        # Verify signature
        verify_result = verify_signature(
            message,
            signature_data["signature"],
            keypair["address"]
        )
        
        assert verify_result["valid"] == True
        assert verify_result["match"] == True
        assert verify_result["recovered_address"].lower() == keypair["address"].lower()
    
    def test_verify_wrong_key_fails(self):
        """Test that verification fails with wrong address"""
        keypair = generate_keypair()
        wrong_keypair = generate_keypair()
        message = "Hello, blockchain!"
        
        # Sign with first key
        signature_data = sign_message(message, keypair["private_key"])
        
        # Try to verify with wrong address
        verify_result = verify_signature(
            message,
            signature_data["signature"],
            wrong_keypair["address"]
        )
        
        assert verify_result["match"] == False
    
    def test_verify_wrong_message_fails(self):
        """Test that verification fails with different message"""
        keypair = generate_keypair()
        message = "Original message"
        different_message = "Different message"
        
        # Sign original message
        signature_data = sign_message(message, keypair["private_key"])
        
        # Try to verify with different message
        verify_result = verify_signature(
            different_message,
            signature_data["signature"],
            keypair["address"]
        )
        
        assert verify_result["match"] == False


class TestContentHashing:
    def test_hash_content_deterministic(self):
        """Test that same content always produces same hash"""
        title = "My Blog Post"
        body = "This is the body of my post"
        
        hash1 = hash_content(title, body)
        hash2 = hash_content(title, body)
        
        assert hash1 == hash2
        assert hash1.startswith("0x")
        assert len(hash1) == 66  # 0x + 64 hex chars
    
    def test_hash_content_different_for_different_input(self):
        """Test that different content produces different hashes"""
        title = "My Blog Post"
        body1 = "This is the body"
        body2 = "This is different body"
        
        hash1 = hash_content(title, body1)
        hash2 = hash_content(title, body2)
        
        assert hash1 != hash2
    
    def test_verify_content_hash(self):
        """Test content hash verification"""
        title = "Post Title"
        body = "Post body content"
        
        content_hash = hash_content(title, body)
        assert verify_content_hash(title, body, content_hash) == True
        
        # Test with wrong hash
        wrong_hash = "0x" + "a" * 64
        assert verify_content_hash(title, body, wrong_hash) == False


class TestDIDDocument:
    def test_create_did_document_schema(self):
        """Test that DID document has correct W3C schema"""
        keypair = generate_keypair()
        
        did_doc = create_did_document(
            keypair["address"],
            keypair["public_key"],
            "https://example.com"
        )
        
        # Check required fields
        assert "@context" in did_doc
        assert "https://www.w3.org/ns/did/v1" in did_doc["@context"]
        
        assert "id" in did_doc
        assert did_doc["id"].startswith("did:eth:")
        
        assert "verificationMethod" in did_doc
        assert len(did_doc["verificationMethod"]) > 0
        
        method = did_doc["verificationMethod"][0]
        assert method["type"] == "EcdsaSecp256k1VerificationKey2019"
        assert method["publicKeyHex"] == keypair["public_key"]
        
        assert "authentication" in did_doc
        assert "service" in did_doc
        
        service = did_doc["service"][0]
        assert service["type"] == "BlogService"
        assert service["serviceEndpoint"] == "https://example.com"
    
    def test_create_did_document_default_endpoint(self):
        """Test that default service endpoint is generated"""
        keypair = generate_keypair()
        
        did_doc = create_did_document(keypair["address"], keypair["public_key"])
        
        service = did_doc["service"][0]
        assert "decentrablog.io" in service["serviceEndpoint"]
        assert keypair["address"] in service["serviceEndpoint"]
    
    def test_create_did_document_consistent(self):
        """Test that DID document is consistent for same input"""
        address = "0x1234567890123456789012345678901234567890"
        public_key = "0x04" + "a" * 128
        
        did_doc1 = create_did_document(address, public_key)
        did_doc2 = create_did_document(address, public_key)
        
        assert did_doc1 == did_doc2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
