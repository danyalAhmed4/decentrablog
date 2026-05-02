import time
import json
from typing import Dict

from eth_account import Account
from eth_account.messages import encode_defunct
from flask import Flask, jsonify, request

from blockchain import BlockchainClient
from crypto import create_ethereum_account, generate_did, generate_nonce

app = Flask(__name__)

# nonce -> {"did": str, "appId": str, "message": str, "expiresAt": int}
nonce_store: Dict[str, Dict[str, str]] = {}
NONCE_TTL_SECONDS = 120


def _cleanup_expired_nonces() -> None:
    now = int(time.time())
    expired = [nonce for nonce, data in nonce_store.items() if now > data["expiresAt"]]
    for nonce in expired:
        nonce_store.pop(nonce, None)


def _get_blockchain_client():
    return BlockchainClient()


@app.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    blockchain = _get_blockchain_client()
    try:
        if blockchain.verify_identity_exists_by_name_email(name, email):
            return (
                jsonify(
                    {
                        "error": "An identity with this name and email is already registered",
                    }
                ),
                409,
            )

        did = generate_did()
        account_data = create_ethereum_account()

        tx_hash = blockchain.register_identity(
            did=did,
            name=name,
            email=email,
            public_key=account_data["publicKey"],
        )
    except ValueError as exc:
        error_message = str(exc)
        if "already registered" in error_message.lower():
            return jsonify({"error": "An identity with this name and email is already registered"}), 409
        return jsonify({"error": f"registration failed: {error_message}"}), 400
    except Exception as exc:
        return jsonify({"error": f"registration failed: {str(exc)}"}), 500

    return jsonify(
        {
            "did": did,
            "publicKey": account_data["publicKey"],
            "privateKey": account_data["privateKey"],
            "privateKeyDownload": json.dumps(
                {
                    "did": did,
                    "privateKey": account_data["privateKey"],
                    "publicKey": account_data["publicKey"],
                },
                indent=2,
            ),
            "txHash": tx_hash,
        }
    )


@app.post("/auth/request-challenge")
def request_challenge():
    payload = request.get_json(silent=True) or {}
    did = (payload.get("did") or "").strip()
    app_id = (payload.get("appId") or "").strip()

    if not did or not app_id:
        return jsonify({"error": "did and appId are required"}), 400

    try:
        blockchain = _get_blockchain_client()
        if not blockchain.verify_did_exists(did):
            return jsonify({"error": "DID does not exist"}), 404

        nonce = generate_nonce()
        timestamp = int(time.time())
        message = f"Login to {app_id} at {timestamp} with nonce {nonce}"
        nonce_store[nonce] = {
            "did": did,
            "appId": app_id,
            "message": message,
            "expiresAt": timestamp + NONCE_TTL_SECONDS,
        }
    except Exception as exc:
        return jsonify({"error": f"challenge creation failed: {str(exc)}"}), 500

    return jsonify({"message": message, "nonce": nonce})


@app.post("/auth/verify")
def verify_auth():
    _cleanup_expired_nonces()

    payload = request.get_json(silent=True) or {}
    did = (payload.get("did") or "").strip()
    message = payload.get("message") or ""
    signature = payload.get("signature") or ""
    nonce = payload.get("nonce") or ""
    app_id = (payload.get("appId") or "").strip()

    if not all([did, message, signature, nonce, app_id]):
        return jsonify({"error": "did, message, signature, nonce, and appId are required"}), 400

    nonce_data = nonce_store.get(nonce)
    if not nonce_data:
        return jsonify({"verified": False, "error": "invalid or expired nonce"}), 400

    now = int(time.time())
    if now > nonce_data["expiresAt"]:
        nonce_store.pop(nonce, None)
        return jsonify({"verified": False, "error": "nonce expired"}), 400

    if nonce_data["did"] != did or nonce_data["appId"] != app_id or nonce_data["message"] != message:
        return jsonify({"verified": False, "error": "challenge data mismatch"}), 400

    try:
        blockchain = _get_blockchain_client()
        if not blockchain.verify_did_exists(did):
            nonce_store.pop(nonce, None)
            return jsonify({"verified": False, "error": "DID does not exist"}), 404

        identity = blockchain.get_identity(did)
        encoded_message = encode_defunct(text=message)
        recovered_address = Account.recover_message(encoded_message, signature=signature)
        verified = recovered_address.lower() == identity["publicKey"].lower()
    except Exception as exc:
        nonce_store.pop(nonce, None)
        return jsonify({"verified": False, "error": f"verification failed: {str(exc)}"}), 500

    nonce_store.pop(nonce, None)
    if verified:
        return jsonify({"verified": True, "name": identity["name"]})
    return jsonify({"verified": False})


@app.get("/identity/<path:did>")
def get_identity(did: str):
    try:
        blockchain = _get_blockchain_client()
        if not blockchain.verify_did_exists(did):
            return jsonify({"error": "DID does not exist"}), 404

        identity = blockchain.get_identity(did)
        return jsonify(identity)
    except Exception as exc:
        return jsonify({"error": f"failed to fetch identity: {str(exc)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
