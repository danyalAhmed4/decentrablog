"""
Flask REST API for DecentraBlog
Main application with all endpoints for DID registration, post publishing, and verification
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from crypto_utils import (
    generate_keypair,
    sign_message,
    verify_signature,
    hash_content,
    create_did_document,
    verify_content_hash
)
from blockchain import BlockchainClient
from models import Base, DIDRecord, BlogPost, init_db


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env", override=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://localhost:5500", "http://127.0.0.1:3000", "http://127.0.0.1:5500"])

# Initialize database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///decentrablog.db")

# Make relative sqlite paths stable regardless of launch directory.
# Example: sqlite:///decentrablog.db -> backend/decentrablog.db
if DATABASE_URL.startswith("sqlite:///") and not DATABASE_URL.startswith("sqlite:////"):
    sqlite_rel_path = DATABASE_URL.replace("sqlite:///", "", 1)
    DATABASE_URL = f"sqlite:///{(BACKEND_DIR / sqlite_rel_path).as_posix()}"

engine = create_engine(DATABASE_URL, echo=False)
init_db(engine)
SessionLocal = sessionmaker(bind=engine)

# Initialize blockchain client
blockchain_client = BlockchainClient()


def get_db() -> Session:
    """Get database session"""
    return SessionLocal()


# ============================================================================
# HEALTH & STATS ENDPOINTS
# ============================================================================

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get system statistics"""
    try:
        db = get_db()
        total_dids = db.query(DIDRecord).count()
        active_dids = db.query(DIDRecord).filter(DIDRecord.is_active == True).count()
        total_posts = db.query(BlogPost).count()
        verified_posts = db.query(BlogPost).filter(BlogPost.chain_verified == True).count()
        db.close()

        return jsonify({
            "total_dids": total_dids,
            "active_dids": active_dids,
            "total_posts": total_posts,
            "verified_posts": verified_posts
        }), 200
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# DID ENDPOINTS
# ============================================================================

@app.route("/api/did/generate", methods=["POST"])
def did_generate():
    """Generate a new keypair and DID"""
    try:
        keypair = generate_keypair()
        return jsonify(keypair), 200
    except Exception as e:
        logger.error(f"Error generating keypair: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/did/register", methods=["POST"])
def did_register():
    """Register a new DID"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["did", "public_key", "address", "display_name", "private_key"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        did = data["did"]
        public_key = data["public_key"]
        address = data["address"]
        display_name = data["display_name"]
        bio = data.get("bio", "")
        private_key = data["private_key"]

        # Create DID document
        service_endpoint = data.get("service_endpoint", "")
        did_document = create_did_document(address, public_key, service_endpoint)

        # Register on blockchain if enabled
        tx_hash = None
        block_number = None
        if blockchain_client.is_enabled():
            bc_result = blockchain_client.register_did(did, public_key, service_endpoint, private_key)
            if bc_result.get("status") == "success":
                tx_hash = bc_result["tx_hash"]
                block_number = bc_result["block"]

        # Save to database
        db = get_db()
        try:
            did_record = DIDRecord(
                did=did,
                address=address,
                public_key=public_key,
                display_name=display_name,
                bio=bio,
                did_document=json.dumps(did_document),
                tx_hash=tx_hash,
                block_number=block_number,
                is_active=True
            )
            db.add(did_record)
            db.commit()
            db.close()
        except IntegrityError:
            db.close()
            return jsonify({"error": "DID or address already registered"}), 409

        return jsonify({
            "success": True,
            "did": did,
            "address": address,
            "display_name": display_name,
            "did_document": did_document,
            "tx_hash": tx_hash,
            "block_number": block_number
        }), 201

    except Exception as e:
        logger.error(f"Error registering DID: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/did/resolve/<address>", methods=["GET"])
def did_resolve(address):
    """Resolve a DID by address"""
    try:
        db = get_db()
        did_record = db.query(DIDRecord).filter(DIDRecord.address == address).first()
        db.close()

        if not did_record:
            return jsonify({"error": "DID not found"}), 404

        return jsonify({
            "did": did_record.did,
            "address": did_record.address,
            "display_name": did_record.display_name,
            "did_document": json.loads(did_record.did_document),
            "created_at": did_record.created_at.isoformat(),
            "is_active": did_record.is_active
        }), 200

    except Exception as e:
        logger.error(f"Error resolving DID: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/did/resolve/string/<did_string>", methods=["GET"])
def did_resolve_string(did_string):
    """Resolve a DID by DID string"""
    try:
        db = get_db()
        did_record = db.query(DIDRecord).filter(DIDRecord.did == did_string).first()
        db.close()

        if not did_record:
            return jsonify({"error": "DID not found"}), 404

        return jsonify({
            "did": did_record.did,
            "address": did_record.address,
            "display_name": did_record.display_name,
            "did_document": json.loads(did_record.did_document),
            "created_at": did_record.created_at.isoformat(),
            "is_active": did_record.is_active
        }), 200

    except Exception as e:
        logger.error(f"Error resolving DID: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# BLOG POST ENDPOINTS
# ============================================================================

@app.route("/api/posts/publish", methods=["POST"])
def publish_post():
    """Publish a new blog post"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ["title", "body", "author_did", "author_address", "private_key"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        title = data["title"]
        body = data["body"]
        author_did = data["author_did"]
        author_address = data["author_address"]
        private_key = data["private_key"]
        tags = data.get("tags", "")

        # Validate title and body not empty
        if not title or not body:
            return jsonify({"error": "Title and body cannot be empty"}), 400

        # Verify author has active DID
        db = get_db()
        did_record = db.query(DIDRecord).filter(DIDRecord.did == author_did).first()
        if not did_record or not did_record.is_active:
            db.close()
            return jsonify({"error": "Author does not have an active DID"}), 400

        # Compute content hash
        content_hash = hash_content(title, body)
        content_hash_bytes = bytes.fromhex(content_hash[2:])

        # Sign content hash
        sign_result = sign_message(content_hash, private_key)
        if not sign_result:
            db.close()
            return jsonify({"error": "Failed to sign content"}), 500

        signature_hex = sign_result["signature"]
        signature_bytes = bytes.fromhex(signature_hex[2:])

        # Verify signature immediately
        verify_result = verify_signature(content_hash, signature_hex, author_address)
        if not verify_result["match"]:
            db.close()
            return jsonify({
                "error": "Signature verification failed",
                "details": verify_result
            }), 400

        # Publish on blockchain if enabled
        tx_hash = None
        block_number = None
        chain_verified = False
        if blockchain_client.is_enabled():
            bc_result = blockchain_client.publish_post_onchain(
                content_hash_bytes, signature_bytes, author_did, private_key
            )
            if bc_result.get("status") == "success":
                tx_hash = bc_result["tx_hash"]
                block_number = bc_result["block"]
                chain_verified = True

        # Save to database
        try:
            blog_post = BlogPost(
                title=title,
                body=body,
                author_did=author_did,
                author_address=author_address,
                content_hash=content_hash,
                signature=signature_hex,
                tags=tags,
                tx_hash=tx_hash,
                block_number=block_number,
                chain_verified=chain_verified
            )
            db.add(blog_post)
            db.commit()
            post_id = blog_post.id
            db.close()
        except Exception as e:
            db.close()
            logger.error(f"Error saving blog post: {e}")
            return jsonify({"error": "Failed to save blog post"}), 500

        return jsonify({
            "success": True,
            "post_id": post_id,
            "content_hash": content_hash,
            "signature": signature_hex,
            "tx_hash": tx_hash,
            "block_number": block_number,
            "chain_verified": chain_verified
        }), 201

    except Exception as e:
        logger.error(f"Error publishing post: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/posts", methods=["GET"])
def get_posts():
    """Get paginated list of blog posts with filters"""
    try:
        # Get query parameters
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 10, type=int)
        tag = request.args.get("tag", None)
        author_did = request.args.get("author_did", None)

        db = get_db()

        # Build query
        query = db.query(BlogPost).order_by(desc(BlogPost.published_at))

        # Apply filters
        if tag:
            query = query.filter(BlogPost.tags.like(f"%{tag}%"))
        if author_did:
            query = query.filter(BlogPost.author_did == author_did)

        # Get total count
        total = query.count()

        # Paginate
        offset = (page - 1) * limit
        posts = query.offset(offset).limit(limit).all()

        # Prepare response
        posts_data = [post.to_dict(include_author=True) for post in posts]
        pages = (total + limit - 1) // limit
        db.close()

        return jsonify({
            "posts": posts_data,
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit
        }), 200

    except Exception as e:
        logger.error(f"Error getting posts: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/posts/<int:post_id>", methods=["GET"])
def get_post(post_id):
    """Get a specific blog post"""
    try:
        db = get_db()
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()

        if not post:
            db.close()
            return jsonify({"error": "Post not found"}), 404

        post_data = post.to_dict(include_author=True)
        db.close()
        return jsonify(post_data), 200

    except Exception as e:
        logger.error(f"Error getting post: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/posts/<int:post_id>/verify", methods=["GET"])
def verify_post(post_id):
    """Verify a blog post signature"""
    try:
        db = get_db()
        post = db.query(BlogPost).filter(BlogPost.id == post_id).first()

        if not post:
            db.close()
            return jsonify({"error": "Post not found"}), 404

        # Verify signature off-chain
        verify_result = verify_signature(post.content_hash, post.signature, post.author_address)

        # Optionally verify on-chain (via tx hash -> on-chain post id)
        chain_verified = False
        if blockchain_client.is_enabled() and post.tx_hash:
            chain_verified = blockchain_client.verify_post_by_tx_hash(post.tx_hash)
            # Persist positive on-chain verification so stats reflect verified posts.
            if chain_verified and not post.chain_verified:
                post.chain_verified = True
                db.commit()

        db.close()

        return jsonify({
            "post_id": post_id,
            "valid": verify_result["match"],
            "recovered_address": verify_result["recovered_address"],
            "expected_address": verify_result["expected_address"],
            "chain_verified": chain_verified
        }), 200

    except Exception as e:
        logger.error(f"Error verifying post: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
