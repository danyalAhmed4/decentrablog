"""
Blockchain interaction layer using web3.py
Handles smart contract calls and transaction management
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
import logging

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)
logger = logging.getLogger(__name__)


class BlockchainClient:
    """
    Client for interacting with DIDRegistry and BlogRegistry smart contracts
    """

    def __init__(self):
        """Initialize blockchain client with web3 provider and contracts"""
        # Load environment variables
        provider_uri = os.getenv("WEB3_PROVIDER_URI", "http://127.0.0.1:8545")
        did_registry_address = os.getenv("DID_REGISTRY_ADDRESS")
        blog_registry_address = os.getenv("BLOG_REGISTRY_ADDRESS")
        deployer_private_key = os.getenv("DEPLOYER_PRIVATE_KEY")

        # Initialize web3
        self.w3 = Web3(Web3.HTTPProvider(provider_uri))

        # Check connection
        if not self.w3.is_connected():
            logger.warning(f"Web3 not connected to {provider_uri}")

        # Store addresses
        self.did_registry_address = Web3.to_checksum_address(did_registry_address) if did_registry_address else None
        self.blog_registry_address = Web3.to_checksum_address(blog_registry_address) if blog_registry_address else None

        # Set deployer account for transactions
        if deployer_private_key:
            self.account = Account.from_key(deployer_private_key)
        else:
            self.account = None

        # Load contract ABIs
        self.did_registry_abi = self._load_abi("DIDRegistry")
        self.blog_registry_abi = self._load_abi("BlogRegistry")

        # Initialize contracts
        if self.did_registry_address and self.did_registry_abi:
            self.did_registry = self.w3.eth.contract(
                address=self.did_registry_address,
                abi=self.did_registry_abi
            )
        else:
            self.did_registry = None

        if self.blog_registry_address and self.blog_registry_abi:
            self.blog_registry = self.w3.eth.contract(
                address=self.blog_registry_address,
                abi=self.blog_registry_abi
            )
        else:
            self.blog_registry = None

    def _load_abi(self, contract_name: str) -> Optional[List]:
        """
        Load contract ABI from abi directory
        
        Args:
            contract_name: Name of contract (e.g., "DIDRegistry")
        
        Returns:
            List: Contract ABI or None if not found
        """
        abi_dir = PROJECT_ROOT / "abi"
        direct_abi_path = abi_dir / f"{contract_name}.json"
        artifact_path = PROJECT_ROOT / "artifacts" / "contracts" / f"{contract_name}.sol" / f"{contract_name}.json"

        # 1) Preferred: plain ABI file in /abi
        if direct_abi_path.exists():
            try:
                with open(direct_abi_path, "r", encoding="utf-8") as f:
                    parsed = json.load(f)
                    return parsed.get("abi") if isinstance(parsed, dict) else parsed
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid ABI JSON in {direct_abi_path}: {e}")

        # 2) Fallback: Hardhat artifact JSON and extract "abi"
        if artifact_path.exists():
            try:
                with open(artifact_path, "r", encoding="utf-8") as f:
                    artifact = json.load(f)
                abi = artifact.get("abi")
                if abi:
                    # Cache extracted ABI for faster startup and simpler tooling.
                    abi_dir.mkdir(parents=True, exist_ok=True)
                    with open(direct_abi_path, "w", encoding="utf-8") as out_f:
                        json.dump(abi, out_f, indent=2)
                    return abi
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid artifact JSON in {artifact_path}: {e}")

        logger.warning(
            "Could not load ABI for %s. Checked %s and %s",
            contract_name,
            direct_abi_path,
            artifact_path,
        )
        return None

    def is_enabled(self) -> bool:
        """Check if blockchain integration is enabled"""
        blockchain_enabled = os.getenv("BLOCKCHAIN_ENABLED", "false").lower() == "true"
        return (
            blockchain_enabled
            and self.w3.is_connected()
            and self.did_registry is not None
            and self.blog_registry is not None
        )

    def register_did(
        self,
        did: str,
        public_key: str,
        service_endpoint: str,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Register a DID on-chain
        
        Args:
            did: DID string (e.g., "did:eth:0x...")
            public_key: Public key hex string
            service_endpoint: Service endpoint URL
            private_key: Private key for signing transaction
        
        Returns:
            dict: { "tx_hash", "block", "gas_used" } or error dict
        """
        if not self.is_enabled():
            return {"error": "Blockchain not enabled", "status": "skipped"}

        try:
            # Create account from private key
            account = Account.from_key(private_key)

            # Build transaction
            tx = self.did_registry.functions.registerDID(
                did, public_key, service_endpoint
            ).build_transaction({
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "gas": 200000,
                "gasPrice": self.w3.eth.gas_price,
            })

            # Sign and send
            signed_tx = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            return {
                "tx_hash": self.w3.to_hex(tx_hash),
                "block": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error registering DID: {e}")
            return {"error": str(e), "status": "failed"}

    def resolve_did(self, address: str) -> Dict[str, Any]:
        """
        Resolve a DID document by address
        
        Args:
            address: Ethereum address
        
        Returns:
            dict: DID document or error dict
        """
        if not self.is_enabled():
            return {"error": "Blockchain not enabled", "status": "skipped"}

        try:
            address = Web3.to_checksum_address(address)
            did_doc = self.did_registry.functions.resolveDID(address).call()

            return {
                "did": did_doc[0],
                "owner": did_doc[1],
                "public_key": did_doc[2],
                "service_endpoint": did_doc[3],
                "created_at": did_doc[4],
                "active": did_doc[5],
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error resolving DID: {e}")
            return {"error": str(e), "status": "failed"}

    def is_did_active(self, address: str) -> bool:
        """
        Check if a DID is active
        
        Args:
            address: Ethereum address
        
        Returns:
            bool: True if active
        """
        if not self.is_enabled():
            return False

        try:
            address = Web3.to_checksum_address(address)
            return self.did_registry.functions.isDIDActive(address).call()
        except Exception as e:
            logger.error(f"Error checking DID active status: {e}")
            return False

    def publish_post_onchain(
        self,
        content_hash_bytes: bytes,
        signature: bytes,
        author_did: str,
        private_key: str
    ) -> Dict[str, Any]:
        """
        Publish a blog post on-chain
        
        Args:
            content_hash_bytes: Content hash as bytes
            signature: ECDSA signature as bytes
            author_did: Author's DID string
            private_key: Private key for signing transaction
        
        Returns:
            dict: { "tx_hash", "post_id", "block" } or error dict
        """
        if not self.is_enabled():
            return {"error": "Blockchain not enabled", "status": "skipped"}

        try:
            # Create account from private key
            account = Account.from_key(private_key)

            # Build transaction
            tx = self.blog_registry.functions.publishPost(
                content_hash_bytes, signature, author_did
            ).build_transaction({
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "gas": 250000,
                "gasPrice": self.w3.eth.gas_price,
            })

            # Sign and send
            signed_tx = account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

            # Extract post ID from event logs (PostPublished event)
            post_id = len(self.blog_registry.functions.posts.call()) - 1

            return {
                "tx_hash": self.w3.to_hex(tx_hash),
                "post_id": post_id,
                "block": receipt["blockNumber"],
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error publishing post: {e}")
            return {"error": str(e), "status": "failed"}

    def verify_post_onchain(self, post_id: int) -> bool:
        """
        Verify a blog post signature on-chain
        
        Args:
            post_id: Post ID
        
        Returns:
            bool: True if signature is valid
        """
        if not self.is_enabled():
            return False

        try:
            return self.blog_registry.functions.verifyPost(post_id).call()
        except Exception as e:
            logger.error(f"Error verifying post: {e}")
            return False

    def verify_post_by_tx_hash(self, tx_hash: str) -> bool:
        """
        Verify a post by resolving its on-chain post ID from transaction hash.

        Args:
            tx_hash: Transaction hash returned when publishing the post

        Returns:
            bool: True if signature is valid on-chain
        """
        if not self.is_enabled() or not tx_hash:
            return False

        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as e:
            logger.warning(f"Could not fetch transaction receipt for {tx_hash}: {e}")
            return False

        post_id = None
        try:
            # Decode PostPublished logs to recover the canonical on-chain post ID.
            for log in receipt.logs:
                try:
                    decoded = self.blog_registry.events.PostPublished().process_log(log)
                    post_id = decoded["args"]["postId"]
                    break
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Could not decode PostPublished logs for {tx_hash}: {e}")
            return False

        if post_id is None:
            logger.warning(f"No PostPublished event found in tx {tx_hash}")
            return False

        return self.verify_post_onchain(post_id)

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a blog post by ID
        
        Args:
            post_id: Post ID
        
        Returns:
            dict: Post data or None
        """
        if not self.is_enabled():
            return None

        try:
            post = self.blog_registry.functions.getPost(post_id).call()

            return {
                "content_hash": self.w3.to_hex(post[0]),
                "author": post[1],
                "did": post[2],
                "signature": self.w3.to_hex(post[3]),
                "published_at": post[4],
                "verified": post[5]
            }
        except Exception as e:
            logger.error(f"Error getting post: {e}")
            return None

    def get_all_posts(self) -> List[Dict[str, Any]]:
        """
        Get all blog posts
        
        Returns:
            list: Array of post objects
        """
        if not self.is_enabled():
            return []

        try:
            post_count = self.blog_registry.functions.getPostCount().call()
            posts = []

            for i in range(post_count):
                post = self.get_post(i)
                if post:
                    post["id"] = i
                    posts.append(post)

            return posts
        except Exception as e:
            logger.error(f"Error getting all posts: {e}")
            return []

    def get_author_posts(self, author_address: str) -> List[int]:
        """
        Get all post IDs by an author
        
        Args:
            author_address: Author's Ethereum address
        
        Returns:
            list: Array of post IDs
        """
        if not self.is_enabled():
            return []

        try:
            author_address = Web3.to_checksum_address(author_address)
            return self.blog_registry.functions.getAuthorPosts(author_address).call()
        except Exception as e:
            logger.error(f"Error getting author posts: {e}")
            return []

    def get_post_count(self) -> int:
        """
        Get total post count
        
        Returns:
            int: Total number of posts
        """
        if not self.is_enabled():
            return 0

        try:
            return self.blog_registry.functions.getPostCount().call()
        except Exception as e:
            logger.error(f"Error getting post count: {e}")
            return 0
