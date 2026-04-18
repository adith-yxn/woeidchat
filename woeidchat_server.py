"""
WoeidChat Server
FastAPI + WebSockets + SQLite
Run: python woeidchat_server.py
"""

import asyncio
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn


# ─── Database ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("woeidchat.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username     TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt         TEXT NOT NULL,
            public_key   TEXT NOT NULL,
            created_at   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            username   TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            sender            TEXT NOT NULL,
            recipient         TEXT NOT NULL,
            encrypted_content TEXT NOT NULL,
            encrypted_key     TEXT NOT NULL,
            timestamp         TEXT NOT NULL,
            delivered         INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()


# ─── Connection Manager ───────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active[username] = websocket
        await self._broadcast_presence(username, "online")

    async def disconnect(self, username: str):
        self.active.pop(username, None)
        await self._broadcast_presence(username, "offline")

    async def _broadcast_presence(self, username: str, status: str):
        payload = json.dumps(
            {"type": "presence", "username": username, "status": status})
        for uname, ws in list(self.active.items()):
            if uname != username:
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass

    async def send_to(self, username: str, data: dict) -> bool:
        ws = self.active.get(username)
        if ws:
            try:
                await ws.send_text(json.dumps(data))
                return True
            except Exception:
                return False
        return False

    def online_users(self):
        return list(self.active.keys())


manager = ConnectionManager()


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def hash_pw(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def verify_token(token: str) -> Optional[str]:
    conn = get_db()
    row = conn.execute(
        "SELECT username FROM sessions WHERE token=?", (token,)).fetchone()
    conn.close()
    return row["username"] if row else None


def auth_header(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    token = authorization.replace("Bearer ", "").strip()
    username = verify_token(token)
    if not username:
        raise HTTPException(401, "Invalid or expired token")
    return username


# ─── Pydantic models ──────────────────────────────────────────────────────────

class RegisterReq(BaseModel):
    username: str
    password: str
    public_key: str


class LoginReq(BaseModel):
    username: str
    password: str


# ─── App ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="WoeidChat", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[
                   "*"], allow_methods=["*"], allow_headers=["*"])


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@app.post("/register")
async def register(req: RegisterReq):
    if len(req.username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if not req.username.isalnum():
        raise HTTPException(400, "Username must be alphanumeric")

    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM users WHERE username=?", (req.username,)).fetchone():
            raise HTTPException(400, "Username already taken")

        salt = secrets.token_hex(16)
        pw_hash = hash_pw(req.password, salt)
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?)",
            (req.username, pw_hash, salt, req.public_key,
             datetime.utcnow().isoformat())
        )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Account created successfully"}


@app.post("/login")
async def login(req: LoginReq):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
        if not row or hash_pw(req.password, row["salt"]) != row["password_hash"]:
            raise HTTPException(401, "Invalid username or password")

        token = secrets.token_hex(32)
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?)",
            (token, req.username, datetime.utcnow().isoformat())
        )
        conn.commit()
    finally:
        conn.close()

    return {"token": token, "username": req.username}


@app.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        conn.close()
    return {"message": "Logged out"}


@app.get("/users")
async def list_users(authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    conn = get_db()
    rows = conn.execute(
        "SELECT username FROM users WHERE username!=?", (me,)).fetchall()
    conn.close()
    return {"users": [r["username"] for r in rows], "online": manager.online_users()}


@app.get("/public-key/{target}")
async def get_public_key(target: str, authorization: Optional[str] = Header(None)):
    auth_header(authorization)
    conn = get_db()
    row = conn.execute(
        "SELECT public_key FROM users WHERE username=?", (target,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "User not found")
    return {"public_key": row["public_key"]}


@app.get("/messages/{other}")
async def get_messages(other: str, authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    conn = get_db()
    rows = conn.execute("""
        SELECT sender, recipient, encrypted_content, encrypted_key, timestamp
        FROM messages
        WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)
        ORDER BY timestamp ASC
    """, (me, other, other, me)).fetchall()
    conn.close()
    return {"messages": [dict(r) for r in rows]}


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/{token}")
async def ws_endpoint(websocket: WebSocket, token: str):
    username = verify_token(token)
    if not username:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    await manager.connect(username, websocket)

    # Deliver pending offline messages
    conn = get_db()
    pending = conn.execute(
        "SELECT sender, encrypted_content, encrypted_key, timestamp FROM messages "
        "WHERE recipient=? AND delivered=0 ORDER BY timestamp ASC",
        (username,)
    ).fetchall()
    for m in pending:
        await manager.send_to(username, {
            "type": "message",
            "sender": m["sender"],
            "encrypted_content": m["encrypted_content"],
            "encrypted_key": m["encrypted_key"],
            "timestamp": m["timestamp"]
        })
    if pending:
        conn.execute(
            "UPDATE messages SET delivered=1 WHERE recipient=? AND delivered=0", (username,))
        conn.commit()
    conn.close()

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                recipient = data["recipient"]
                enc_content = data["encrypted_content"]
                enc_key = data["encrypted_key"]
                ts = datetime.utcnow().isoformat()

                # Forward in real-time if online
                delivered = await manager.send_to(recipient, {
                    "type": "message",
                    "sender": username,
                    "encrypted_content": enc_content,
                    "encrypted_key": enc_key,
                    "timestamp": ts
                })

                # Persist
                conn = get_db()
                conn.execute(
                    "INSERT INTO messages (sender,recipient,encrypted_content,encrypted_key,timestamp,delivered) "
                    "VALUES (?,?,?,?,?,?)",
                    (username, recipient, enc_content,
                     enc_key, ts, 1 if delivered else 0)
                )
                conn.commit()
                conn.close()

                # Ack to sender
                await websocket.send_text(json.dumps({"type": "ack", "timestamp": ts, "recipient": recipient}))

            elif data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        await manager.disconnect(username)


if __name__ == "__main__":
    print("\n" + "═"*50)
    print("  🔐 WoeidChat Server")
    print("  Listening on http://0.0.0.0:8765")
    print("═"*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")
