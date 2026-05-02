import os
import secrets
import sqlite3
import time
import json
from pathlib import Path
from typing import Optional
from urllib import error, request

from flask import Flask, jsonify, request as flask_request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "blog.db"

DID_API_BASE = os.getenv("DID_API_BASE", "http://127.0.0.1:5000")
SESSION_TTL_SECONDS = 60 * 60 * 24

app = Flask(__name__, static_folder="static")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                did TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                did TEXT NOT NULL,
                author_name TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def did_api_post(path: str, payload: dict) -> tuple[dict, int]:
    url = f"{DID_API_BASE}{path}"
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            return data, response.status
    except error.HTTPError as http_error:
        try:
            raw_error = http_error.read().decode("utf-8")
            parsed = json.loads(raw_error) if raw_error else {}
            return parsed, http_error.code
        except Exception:
            return {"error": f"DID API error: {http_error.reason}"}, http_error.code
    except Exception as exc:
        return {"error": f"Could not connect to DID API: {str(exc)}"}, 500


def create_session(did: str, name: str) -> str:
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    expires_at = now + SESSION_TTL_SECONDS

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO sessions (token, did, name, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, did, name, now, expires_at),
        )
        conn.commit()
    finally:
        conn.close()

    return token


def get_session(token: str) -> Optional[sqlite3.Row]:
    now = int(time.time())
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            return None
        if now > row["expires_at"]:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return row
    finally:
        conn.close()


def delete_session(token: str) -> None:
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()


def extract_token() -> Optional[str]:
    auth_header = flask_request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :].strip()
    return None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.post("/api/auth/request-challenge")
def request_challenge():
    payload = flask_request.get_json(silent=True) or {}
    did = (payload.get("did") or "").strip()
    app_id = (payload.get("appId") or "did-blog").strip()

    if not did:
        return jsonify({"error": "did is required"}), 400

    response_data, status = did_api_post(
        "/auth/request-challenge",
        {"did": did, "appId": app_id},
    )
    return jsonify(response_data), status


@app.post("/api/auth/verify")
def verify_auth():
    payload = flask_request.get_json(silent=True) or {}
    did = (payload.get("did") or "").strip()
    message = payload.get("message") or ""
    signature = payload.get("signature") or ""
    nonce = payload.get("nonce") or ""
    app_id = (payload.get("appId") or "did-blog").strip()

    if not all([did, message, signature, nonce, app_id]):
        return jsonify({"error": "did, message, signature, nonce, and appId are required"}), 400

    verify_data, verify_status = did_api_post(
        "/auth/verify",
        {
            "did": did,
            "message": message,
            "signature": signature,
            "nonce": nonce,
            "appId": app_id,
        },
    )
    if verify_status != 200 or not verify_data.get("verified"):
        return jsonify(verify_data), verify_status

    session_token = create_session(did=did, name=verify_data.get("name", "User"))
    return jsonify(
        {
            "verified": True,
            "name": verify_data.get("name", "User"),
            "token": session_token,
        }
    )


@app.get("/api/auth/me")
def me():
    token = extract_token()
    if not token:
        return jsonify({"error": "missing auth token"}), 401

    session = get_session(token)
    if not session:
        return jsonify({"error": "invalid or expired session"}), 401

    return jsonify({"did": session["did"], "name": session["name"]})


@app.post("/api/auth/logout")
def logout():
    token = extract_token()
    if not token:
        return jsonify({"error": "missing auth token"}), 401
    delete_session(token)
    return jsonify({"loggedOut": True})


@app.get("/api/posts")
def list_posts():
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, did, author_name, title, content, created_at FROM posts ORDER BY id DESC"
        ).fetchall()
        posts = [dict(row) for row in rows]
        return jsonify({"posts": posts})
    finally:
        conn.close()


@app.post("/api/posts")
def create_post():
    token = extract_token()
    if not token:
        return jsonify({"error": "missing auth token"}), 401

    session = get_session(token)
    if not session:
        return jsonify({"error": "invalid or expired session"}), 401

    payload = flask_request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()

    if not title or not content:
        return jsonify({"error": "title and content are required"}), 400

    now = int(time.time())
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO posts (did, author_name, title, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["did"], session["name"], title, content, now),
        )
        conn.commit()
        post_id = cursor.lastrowid
    finally:
        conn.close()

    return jsonify(
        {
            "id": post_id,
            "did": session["did"],
            "author_name": session["name"],
            "title": title,
            "content": content,
            "created_at": now,
        }
    )


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
