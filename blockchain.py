import json
import os
from typing import Dict

from web3 import Web3
from web3.exceptions import ContractLogicError


class BlockchainClient:
    def __init__(self) -> None:
        rpc_url = os.getenv("RPC_URL", "http://127.0.0.1:8545")
        contract_address = os.getenv("DID_CONTRACT_ADDRESS")
        abi_path = os.getenv("DID_CONTRACT_ABI_PATH", "DIDRegistry.abi.json")
        relayer_private_key = os.getenv("RELAYER_PRIVATE_KEY")

        if not contract_address:
            raise ValueError("DID_CONTRACT_ADDRESS is not set.")
        if not relayer_private_key:
            raise ValueError("RELAYER_PRIVATE_KEY is not set.")

        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.web3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC endpoint: {rpc_url}")

        with open(abi_path, "r", encoding="utf-8") as abi_file:
            contract_abi = json.load(abi_file)

        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=contract_abi,
        )
        self.relayer_account = self.web3.eth.account.from_key(relayer_private_key)

    def register_identity(self, did: str, name: str, email: str, public_key: str) -> str:
        public_key_checksum = Web3.to_checksum_address(public_key)
        try:
            tx = self.contract.functions.registerIdentity(
                did,
                name,
                email,
                public_key_checksum,
            ).build_transaction(
                {
                    "from": self.relayer_account.address,
                    "nonce": self.web3.eth.get_transaction_count(self.relayer_account.address),
                    "gas": 400_000,
                    "gasPrice": self.web3.eth.gas_price,
                }
            )

            signed_tx = self.web3.eth.account.sign_transaction(
                tx,
                private_key=self.relayer_account.key,
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            self.web3.eth.wait_for_transaction_receipt(tx_hash)
            return tx_hash.hex()
        except ContractLogicError as exc:
            raise ValueError(str(exc)) from exc

    def verify_did_exists(self, did: str) -> bool:
        return self.contract.functions.verifyDIDExists(did).call()

    def verify_identity_exists_by_name_email(self, name: str, email: str) -> bool:
        return self.contract.functions.verifyIdentityExistsByNameEmail(name, email).call()

    def get_identity(self, did: str) -> Dict[str, str]:
        name, email, public_key = self.contract.functions.getIdentity(did).call()
        return {
            "did": did,
            "name": name,
            "email": email,
            "publicKey": public_key,
        }
