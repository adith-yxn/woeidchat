"""
WoeidChat Server - Enhanced with WhatsApp-like Features
FastAPI + WebSockets + SQLite + File Upload
Run: python woeidchat_server_enhanced.py
"""

import asyncio
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn


# ─── Configuration ─────────────────────────────────────────────────────────

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.pdf', '.txt'}


# ─── Database ──────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("woeidchat.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username         TEXT PRIMARY KEY,
            password_hash    TEXT NOT NULL,
            salt             TEXT NOT NULL,
            public_key       TEXT NOT NULL,
            avatar_url       TEXT,
            status_message   TEXT DEFAULT '',
            created_at       TEXT NOT NULL,
            last_seen        TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            token            TEXT PRIMARY KEY,
            username         TEXT NOT NULL,
            created_at       TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            sender              TEXT NOT NULL,
            recipient           TEXT NOT NULL,
            encrypted_content   TEXT NOT NULL,
            encrypted_key       TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            delivered           INTEGER DEFAULT 0,
            read                INTEGER DEFAULT 0,
            read_at             TEXT,
            message_type        TEXT DEFAULT 'text'
        );
        
        CREATE TABLE IF NOT EXISTS groups (
            group_id        TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            creator         TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            description     TEXT
        );
        
        CREATE TABLE IF NOT EXISTS group_members (
            group_id    TEXT NOT NULL,
            member      TEXT NOT NULL,
            role        TEXT DEFAULT 'member',
            joined_at   TEXT NOT NULL,
            PRIMARY KEY (group_id, member),
            FOREIGN KEY (group_id) REFERENCES groups(group_id)
        );
        
        CREATE TABLE IF NOT EXISTS group_messages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id            TEXT NOT NULL,
            sender              TEXT NOT NULL,
            encrypted_content   TEXT NOT NULL,
            encrypted_key       TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            message_type        TEXT DEFAULT 'text',
            FOREIGN KEY (group_id) REFERENCES groups(group_id)
        );
        
        CREATE TABLE IF NOT EXISTS typing_status (
            username    TEXT PRIMARY KEY,
            is_typing   INTEGER,
            target      TEXT,
            timestamp   TEXT
        );
        
        CREATE TABLE IF NOT EXISTS reactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id  INTEGER NOT NULL,
            user        TEXT NOT NULL,
            emoji       TEXT NOT NULL,
            UNIQUE(message_id, user, emoji)
        );
        
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);
        CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient);
        CREATE INDEX IF NOT EXISTS idx_group_messages_group ON group_messages(group_id);
    """)
    conn.commit()
    conn.close()


# ─── Connection Manager ────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, WebSocket] = {}
        self.typing_status: Dict[str, tuple] = {}

    async def connect(self, username: str, websocket: WebSocket):
        await websocket.accept()
        self.active[username] = websocket
        await self._update_last_seen(username)
        await self._broadcast_presence(username, "online")

    async def disconnect(self, username: str):
        self.active.pop(username, None)
        self.typing_status.pop(username, None)
        await self._update_last_seen(username)
        await self._broadcast_presence(username, "offline")

    async def _update_last_seen(self, username: str):
        conn = get_db()
        conn.execute(
            "UPDATE users SET last_seen=? WHERE username=?",
            (datetime.utcnow().isoformat(), username)
        )
        conn.commit()
        conn.close()

    async def _broadcast_presence(self, username: str, status: str):
        payload = json.dumps({
            "type": "presence",
            "username": username,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        for uname, ws in list(self.active.items()):
            if uname != username:
                try:
                    await ws.send_text(payload)
                except Exception:
                    pass

    async def set_typing(self, username: str, target: str, is_typing: bool):
        if is_typing:
            self.typing_status[username] = (target, datetime.utcnow())
        else:
            self.typing_status.pop(username, None)

        payload = json.dumps({
            "type": "typing",
            "username": username,
            "is_typing": is_typing,
            "target": target
        })
        ws = self.active.get(target)
        if ws:
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

    async def broadcast_to_group(self, group_members: List[str], data: dict, exclude: str = None):
        payload = json.dumps(data)
        for member in group_members:
            if member != exclude:
                ws = self.active.get(member)
                if ws:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        pass

    def online_users(self):
        return list(self.active.keys())


manager = ConnectionManager()


# ─── Auth helpers ──────────────────────────────────────────────────────────

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


# ─── Pydantic models ───────────────────────────────────────────────────────

class RegisterReq(BaseModel):
    username: str
    password: str
    public_key: str


class LoginReq(BaseModel):
    username: str
    password: str


class UpdateProfileReq(BaseModel):
    status_message: Optional[str] = None
    avatar_url: Optional[str] = None


class CreateGroupReq(BaseModel):
    name: str
    member_usernames: List[str]
    description: Optional[str] = None


# ─── App ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="WoeidChat Enhanced", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ─── REST Endpoints ────────────────────────────────────────────────────────

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
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
            (req.username, pw_hash, salt, req.public_key, None, "", now, now)
        )
        conn.commit()
    finally:
        conn.close()

    return {"message": "Account created successfully", "username": req.username}


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

    return {
        "token": token,
        "username": req.username,
        "status_message": row["status_message"],
        "last_seen": row["last_seen"]
    }


@app.get("/users")
async def list_users(authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    conn = get_db()
    rows = conn.execute(
        "SELECT username, status_message, avatar_url FROM users WHERE username!=?", (me,)).fetchall()
    conn.close()
    return {
        "users": [dict(r) for r in rows],
        "online": manager.online_users()
    }


@app.get("/user/{username}")
async def get_user_profile(username: str, authorization: Optional[str] = Header(None)):
    auth_header(authorization)
    conn = get_db()
    row = conn.execute(
        "SELECT username, status_message, avatar_url, last_seen FROM users WHERE username=?",
        (username,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "User not found")
    return dict(row)


@app.put("/profile")
async def update_profile(req: UpdateProfileReq, authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    conn = get_db()
    if req.status_message:
        conn.execute("UPDATE users SET status_message=? WHERE username=?", (req.status_message, me))
    if req.avatar_url:
        conn.execute("UPDATE users SET avatar_url=? WHERE username=?", (req.avatar_url, me))
    conn.commit()
    conn.close()
    return {"message": "Profile updated"}


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
        SELECT id, sender, recipient, encrypted_content, encrypted_key, timestamp, delivered, read, message_type
        FROM messages
        WHERE (sender=? AND recipient=?) OR (sender=? AND recipient=?)
        ORDER BY timestamp ASC
    """, (me, other, other, me)).fetchall()
    
    # Mark as delivered
    conn.execute(
        "UPDATE messages SET delivered=1 WHERE recipient=? AND sender=? AND delivered=0",
        (me, other)
    )
    conn.commit()
    conn.close()
    
    return {"messages": [dict(r) for r in rows]}


@app.post("/messages/{msg_id}/read")
async def mark_message_read(msg_id: int, authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    conn = get_db()
    conn.execute(
        "UPDATE messages SET read=1, read_at=? WHERE id=? AND recipient=?",
        (datetime.utcnow().isoformat(), msg_id, me)
    )
    conn.commit()
    conn.close()
    return {"message": "Marked as read"}


@app.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        conn.close()
    return {"message": "Logged out"}


# ─── Group Endpoints ───────────────────────────────────────────────────────

@app.post("/groups")
async def create_group(req: CreateGroupReq, authorization: Optional[str] = Header(None)):
    creator = auth_header(authorization)
    group_id = secrets.token_hex(16)
    now = datetime.utcnow().isoformat()
    
    conn = get_db()
    conn.execute(
        "INSERT INTO groups VALUES (?,?,?,?,?)",
        (group_id, req.name, creator, now, req.description or "")
    )
    
    # Add creator and members
    all_members = [creator] + req.member_usernames
    for member in all_members:
        conn.execute(
            "INSERT INTO group_members VALUES (?,?,?,?)",
            (group_id, member, "admin" if member == creator else "member", now)
        )
    
    conn.commit()
    conn.close()
    
    return {"group_id": group_id, "name": req.name}


@app.get("/groups")
async def list_groups(authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    conn = get_db()
    rows = conn.execute("""
        SELECT g.group_id, g.name, g.description, COUNT(m.member) as member_count
        FROM groups g
        LEFT JOIN group_members m ON g.group_id = m.group_id
        WHERE g.group_id IN (SELECT group_id FROM group_members WHERE member=?)
        GROUP BY g.group_id
    """, (me,)).fetchall()
    conn.close()
    return {"groups": [dict(r) for r in rows]}


# ─── WebSocket ─────────────────────────────────────────────────────────────

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
        "SELECT id, sender, encrypted_content, encrypted_key, timestamp, message_type FROM messages "
        "WHERE recipient=? AND delivered=0 ORDER BY timestamp ASC",
        (username,)
    ).fetchall()
    for m in pending:
        await manager.send_to(username, {
            "type": "message",
            "id": m["id"],
            "sender": m["sender"],
            "encrypted_content": m["encrypted_content"],
            "encrypted_key": m["encrypted_key"],
            "timestamp": m["timestamp"],
            "message_type": m["message_type"]
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
                msg_type = data.get("message_type", "text")
                ts = datetime.utcnow().isoformat()

                # Forward in real-time if online
                delivered = await manager.send_to(recipient, {
                    "type": "message",
                    "sender": username,
                    "encrypted_content": enc_content,
                    "encrypted_key": enc_key,
                    "timestamp": ts,
                    "message_type": msg_type
                })

                # Persist
                conn = get_db()
                cursor = conn.execute(
                    "INSERT INTO messages (sender,recipient,encrypted_content,encrypted_key,timestamp,delivered,message_type) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (username, recipient, enc_content, enc_key, ts, 1 if delivered else 0, msg_type)
                )
                msg_id = cursor.lastrowid
                conn.commit()
                conn.close()

                # Ack to sender
                await websocket.send_text(json.dumps({
                    "type": "ack",
                    "timestamp": ts,
                    "recipient": recipient,
                    "message_id": msg_id
                }))

            elif data.get("type") == "typing":
                target = data.get("target")
                is_typing = data.get("is_typing", False)
                await manager.set_typing(username, target, is_typing)

            elif data.get("type") == "read":
                sender = data.get("sender")
                msg_id = data.get("message_id")
                conn = get_db()
                conn.execute(
                    "UPDATE messages SET read=1, read_at=? WHERE id=?",
                    (datetime.utcnow().isoformat(), msg_id)
                )
                conn.commit()
                conn.close()
                await manager.send_to(sender, {
                    "type": "read_receipt",
                    "message_id": msg_id,
                    "reader": username
                })

            elif data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        await manager.disconnect(username)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    me = auth_header(authorization)
    
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large")
    
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "File type not allowed")
    
    filename = f"{secrets.token_hex(8)}{ext}"
    filepath = UPLOAD_DIR / filename
    
    contents = await file.read()
    with open(filepath, "wb") as f:
        f.write(contents)
    
    return {
        "url": f"/uploads/{filename}",
        "filename": filename,
        "size": len(contents)
    }


if __name__ == "__main__":
    print("\n" + "═"*60)
    print("  🔐 WoeidChat Server - Enhanced")
    print("  Listening on http://0.0.0.0:8765")
    print("  Features: E2E Encryption, Groups, Typing, File Upload")
    print("═"*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="warning")
