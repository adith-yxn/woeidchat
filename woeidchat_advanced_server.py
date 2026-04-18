"""
WoeidChat Advanced Server - Production Ready
Features: User Discovery, Groups (300+ members), Password Recovery, Profiles, E2E Encryption
Run: python woeidchat_advanced_server.py
"""

import asyncio
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Set
from contextlib import asynccontextmanager
import os
from pathlib import Path
import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn


# ─── Configuration ─────────────────────────────────────────────────────────

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.pdf', '.txt', '.doc', '.docx', '.zip'}
MAX_GROUP_MEMBERS = 500  # Support up to 500 members per group


# ─── Database ──────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("woeidchat_advanced.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id              TEXT PRIMARY KEY,
            username             TEXT UNIQUE NOT NULL,
            password_hash        TEXT NOT NULL,
            salt                 TEXT NOT NULL,
            public_key           TEXT NOT NULL,
            avatar_url           TEXT,
            bio                  TEXT DEFAULT '',
            status_message       TEXT DEFAULT 'Hey, I am using WoeidChat!',
            password_hint        TEXT,
            online_status        INTEGER DEFAULT 0,
            created_at           TEXT NOT NULL,
            last_seen            TEXT NOT NULL,
            verified             INTEGER DEFAULT 0,
            follower_count       INTEGER DEFAULT 0,
            following_count      INTEGER DEFAULT 0
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            token                TEXT PRIMARY KEY,
            user_id              TEXT NOT NULL,
            username             TEXT NOT NULL,
            created_at           TEXT NOT NULL,
            expires_at           TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            message_id           TEXT PRIMARY KEY,
            sender_id            TEXT NOT NULL,
            recipient_id         TEXT NOT NULL,
            encrypted_content    TEXT NOT NULL,
            encrypted_key        TEXT NOT NULL,
            timestamp            TEXT NOT NULL,
            delivered            INTEGER DEFAULT 0,
            read                 INTEGER DEFAULT 0,
            read_at              TEXT,
            message_type         TEXT DEFAULT 'text',
            file_url             TEXT,
            FOREIGN KEY (sender_id) REFERENCES users(user_id),
            FOREIGN KEY (recipient_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS groups (
            group_id             TEXT PRIMARY KEY,
            group_name           TEXT NOT NULL,
            creator_id           TEXT NOT NULL,
            group_photo          TEXT,
            description          TEXT,
            is_public            INTEGER DEFAULT 1,
            created_at           TEXT NOT NULL,
            member_count         INTEGER DEFAULT 1,
            FOREIGN KEY (creator_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS group_members (
            group_id             TEXT NOT NULL,
            member_id            TEXT NOT NULL,
            role                 TEXT DEFAULT 'member',
            joined_at            TEXT NOT NULL,
            is_muted             INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, member_id),
            FOREIGN KEY (group_id) REFERENCES groups(group_id),
            FOREIGN KEY (member_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS group_messages (
            message_id           TEXT PRIMARY KEY,
            group_id             TEXT NOT NULL,
            sender_id            TEXT NOT NULL,
            encrypted_content    TEXT NOT NULL,
            encrypted_key        TEXT NOT NULL,
            timestamp            TEXT NOT NULL,
            message_type         TEXT DEFAULT 'text',
            file_url             TEXT,
            FOREIGN KEY (group_id) REFERENCES groups(group_id),
            FOREIGN KEY (sender_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS follows (
            follower_id          TEXT NOT NULL,
            following_id         TEXT NOT NULL,
            created_at           TEXT NOT NULL,
            PRIMARY KEY (follower_id, following_id),
            FOREIGN KEY (follower_id) REFERENCES users(user_id),
            FOREIGN KEY (following_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS typing_status (
            user_id              TEXT PRIMARY KEY,
            is_typing            INTEGER,
            target_id            TEXT,
            target_type          TEXT,
            timestamp            TEXT
        );
        
        CREATE TABLE IF NOT EXISTS reactions (
            reaction_id          TEXT PRIMARY KEY,
            message_id           TEXT NOT NULL,
            user_id              TEXT NOT NULL,
            emoji                TEXT NOT NULL,
            timestamp            TEXT NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
        CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);
        CREATE INDEX IF NOT EXISTS idx_group_messages_group ON group_messages(group_id);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
    """)
    conn.commit()
    conn.close()


# ─── Connection Manager with Rooms ────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_users: Dict[str, WebSocket] = {}  # user_id -> WebSocket
        self.user_typing: Dict[str, str] = {}  # user_id -> target_id
        self.group_connections: Dict[str, Set[str]] = {}  # group_id -> set of user_ids
        self.lock = asyncio.Lock()

    async def connect_user(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_users[user_id] = websocket
        await self._broadcast_presence(user_id, "online")

    async def disconnect_user(self, user_id: str):
        async with self.lock:
            self.active_users.pop(user_id, None)
            self.user_typing.pop(user_id, None)
        await self._broadcast_presence(user_id, "offline")

    async def join_group(self, group_id: str, user_id: str):
        if group_id not in self.group_connections:
            self.group_connections[group_id] = set()
        async with self.lock:
            self.group_connections[group_id].add(user_id)

    async def leave_group(self, group_id: str, user_id: str):
        if group_id in self.group_connections:
            async with self.lock:
                self.group_connections[group_id].discard(user_id)

    async def send_personal(self, recipient_id: str, message: dict):
        if recipient_id in self.active_users:
            try:
                await self.active_users[recipient_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to {recipient_id}: {e}")

    async def send_to_group(self, group_id: str, message: dict, exclude_user: str = None):
        if group_id in self.group_connections:
            for user_id in self.group_connections[group_id]:
                if exclude_user and user_id == exclude_user:
                    continue
                if user_id in self.active_users:
                    try:
                        await self.active_users[user_id].send_json(message)
                    except Exception:
                        pass

    async def broadcast(self, message: dict, exclude_user: str = None):
        for user_id, ws in list(self.active_users.items()):
            if exclude_user and user_id == exclude_user:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def _broadcast_presence(self, user_id: str, status: str):
        payload = {"type": "presence", "user_id": user_id, "status": status, "timestamp": datetime.now().isoformat()}
        await self.broadcast(payload, exclude_user=user_id)


# ─── Pydantic Models ──────────────────────────────────────────────────────

class RegisterReq(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6)
    password_hint: str = Field(..., min_length=3)
    public_key: str

class LoginReq(BaseModel):
    username: str
    password: str

class UpdateProfileReq(BaseModel):
    bio: Optional[str] = None
    status_message: Optional[str] = None
    avatar_url: Optional[str] = None

class CreateGroupReq(BaseModel):
    group_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_public: bool = True

class AddGroupMemberReq(BaseModel):
    member_id: str

class SendMessageReq(BaseModel):
    content: str
    encrypted_key: str

class SendGroupMessageReq(BaseModel):
    group_id: str
    content: str
    encrypted_key: str


# ─── Utility Functions ────────────────────────────────────────────────────

def hash_pw(password: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000)
    return pw_hash.hex(), salt

def verify_pw(password: str, pw_hash: str, salt: str):
    calculated_hash, _ = hash_pw(password, salt)
    return calculated_hash == pw_hash

def generate_token():
    return secrets.token_urlsafe(32)

def generate_id():
    return secrets.token_urlsafe(16)

def get_current_time():
    return datetime.now().isoformat()


# ─── FastAPI App ──────────────────────────────────────────────────────────

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="WoeidChat Advanced", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Authentication Endpoints ──────────────────────────────────────────────

@app.post("/register")
async def register(req: RegisterReq):
    """Register new user with password hint"""
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", req.username):
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, underscore")
    
    conn = get_db()
    c = conn.cursor()
    
    # Check if username exists
    c.execute("SELECT user_id FROM users WHERE username = ?", (req.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Username already taken")
    
    try:
        user_id = generate_id()
        pw_hash, salt = hash_pw(req.password)
        now = get_current_time()
        
        c.execute("""
            INSERT INTO users (user_id, username, password_hash, salt, public_key, password_hint, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, req.username, pw_hash, salt, req.public_key, req.password_hint, now, now))
        conn.commit()
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user_id,
            "username": req.username
        }
    finally:
        conn.close()


@app.post("/login")
async def login(req: LoginReq):
    """Login with username and password"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id, username, password_hash, salt, public_key FROM users WHERE username = ?", (req.username,))
    user = c.fetchone()
    
    if not user or not verify_pw(req.password, user['password_hash'], user['salt']):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    try:
        token = generate_token()
        expires = (datetime.now() + timedelta(days=7)).isoformat()
        
        c.execute("""
            INSERT INTO sessions (token, user_id, username, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (token, user['user_id'], user['username'], get_current_time(), expires))
        conn.commit()
        
        # Update last seen
        c.execute("UPDATE users SET last_seen = ?, online_status = 1 WHERE user_id = ?", 
                 (get_current_time(), user['user_id']))
        conn.commit()
        
        return {
            "success": True,
            "token": token,
            "user_id": user['user_id'],
            "username": user['username'],
            "public_key": user['public_key']
        }
    finally:
        conn.close()


@app.post("/forgot-password")
async def forgot_password(username: str = Query(...)):
    """Get password hint for recovery"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT password_hint FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "username": username,
        "hint": user['password_hint'],
        "message": "Use this hint to remember your password"
    }


@app.post("/logout")
async def logout(authorization: str = Header(...)):
    """Logout user"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Logged out successfully"}


# ─── User Discovery & Profile Endpoints ─────────────────────────────────

@app.get("/search-users")
async def search_users(query: str = Query(..., min_length=1), authorization: str = Header(...)):
    """Search users by username"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    # Verify token
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    current_user_id = session['user_id']
    
    # Search for users
    c.execute("""
        SELECT user_id, username, avatar_url, bio, status_message, online_status, follower_count
        FROM users 
        WHERE username LIKE ? AND user_id != ?
        LIMIT 20
    """, (f"%{query}%", current_user_id))
    
    users = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "results": users,
        "count": len(users)
    }


@app.get("/user/{username}")
async def get_user_profile(username: str, authorization: str = Header(...)):
    """Get user profile by username"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    # Verify token
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    c.execute("""
        SELECT user_id, username, avatar_url, bio, status_message, online_status, 
               follower_count, following_count, created_at
        FROM users 
        WHERE username = ?
    """, (username,))
    
    user = c.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "success": True,
        "user": dict(user)
    }


@app.post("/profile")
async def update_profile(req: UpdateProfileReq, authorization: str = Header(...)):
    """Update user profile"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session['user_id']
    updates = []
    values = []
    
    if req.bio is not None:
        updates.append("bio = ?")
        values.append(req.bio)
    if req.status_message is not None:
        updates.append("status_message = ?")
        values.append(req.status_message)
    if req.avatar_url is not None:
        updates.append("avatar_url = ?")
        values.append(req.avatar_url)
    
    if updates:
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
        c.execute(query, values)
        conn.commit()
    
    conn.close()
    return {"success": True, "message": "Profile updated"}


# ─── Follow System ────────────────────────────────────────────────────────

@app.post("/follow/{target_username}")
async def follow_user(target_username: str, authorization: str = Header(...)):
    """Follow a user"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    follower_id = session['user_id']
    
    c.execute("SELECT user_id FROM users WHERE username = ?", (target_username,))
    target_user = c.fetchone()
    if not target_user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")
    
    following_id = target_user['user_id']
    
    if follower_id == following_id:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    try:
        c.execute("""
            INSERT INTO follows (follower_id, following_id, created_at)
            VALUES (?, ?, ?)
        """, (follower_id, following_id, get_current_time()))
        
        c.execute("UPDATE users SET follower_count = follower_count + 1 WHERE user_id = ?", (following_id,))
        c.execute("UPDATE users SET following_count = following_count + 1 WHERE user_id = ?", (follower_id,))
        conn.commit()
        
        return {"success": True, "message": "Followed successfully"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Already following"}
    finally:
        conn.close()


# ─── Group Endpoints ──────────────────────────────────────────────────────

@app.post("/groups/create")
async def create_group(req: CreateGroupReq, authorization: str = Header(...)):
    """Create new group (up to 500 members)"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    creator_id = session['user_id']
    group_id = generate_id()
    now = get_current_time()
    
    try:
        c.execute("""
            INSERT INTO groups (group_id, group_name, creator_id, description, is_public, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (group_id, req.group_name, creator_id, req.description or "", req.is_public, now))
        
        c.execute("""
            INSERT INTO group_members (group_id, member_id, role, joined_at)
            VALUES (?, ?, ?, ?)
        """, (group_id, creator_id, 'admin', now))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "group_id": group_id,
            "message": "Group created successfully"
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/groups")
async def list_groups(authorization: str = Header(...)):
    """List all public groups"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    c.execute("""
        SELECT group_id, group_name, description, member_count, created_at
        FROM groups 
        WHERE is_public = 1
        ORDER BY member_count DESC
        LIMIT 50
    """)
    
    groups = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return {"success": True, "groups": groups}


@app.post("/groups/{group_id}/join")
async def join_group(group_id: str, authorization: str = Header(...)):
    """Join a group (max 500 members)"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session['user_id']
    
    c.execute("SELECT member_count FROM groups WHERE group_id = ?", (group_id,))
    group = c.fetchone()
    if not group:
        conn.close()
        raise HTTPException(status_code=404, detail="Group not found")
    
    if group['member_count'] >= MAX_GROUP_MEMBERS:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Group is full (max {MAX_GROUP_MEMBERS} members)")
    
    try:
        c.execute("""
            INSERT INTO group_members (group_id, member_id, role, joined_at)
            VALUES (?, ?, ?, ?)
        """, (group_id, user_id, 'member', get_current_time()))
        
        c.execute("UPDATE groups SET member_count = member_count + 1 WHERE group_id = ?", (group_id,))
        conn.commit()
        
        await manager.join_group(group_id, user_id)
        
        return {"success": True, "message": "Joined group successfully"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Already member of this group"}
    finally:
        conn.close()


@app.get("/groups/{group_id}/members")
async def list_group_members(group_id: str, authorization: str = Header(...)):
    """List group members"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    c.execute("""
        SELECT u.user_id, u.username, u.avatar_url, u.online_status, gm.role
        FROM group_members gm
        JOIN users u ON gm.member_id = u.user_id
        WHERE gm.group_id = ?
        ORDER BY gm.role DESC, u.username
    """, (group_id,))
    
    members = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return {
        "success": True,
        "members": members,
        "count": len(members)
    }


# ─── WebSocket Endpoint ────────────────────────────────────────────────────

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket for real-time messaging"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id, username FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    conn.close()
    
    if not session:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    user_id = session['user_id']
    
    await manager.connect_user(user_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "message":
                recipient_id = data.get("recipient_id")
                message_id = generate_id()
                await manager.send_personal(recipient_id, {
                    "type": "message",
                    "message_id": message_id,
                    "sender_id": user_id,
                    "content": data.get("content"),
                    "encrypted_key": data.get("encrypted_key"),
                    "timestamp": get_current_time()
                })
            
            elif msg_type == "group_message":
                group_id = data.get("group_id")
                message_id = generate_id()
                await manager.send_to_group(group_id, {
                    "type": "group_message",
                    "message_id": message_id,
                    "sender_id": user_id,
                    "group_id": group_id,
                    "content": data.get("content"),
                    "encrypted_key": data.get("encrypted_key"),
                    "timestamp": get_current_time()
                }, exclude_user=user_id)
            
            elif msg_type == "typing":
                target_id = data.get("target_id")
                await manager.send_personal(target_id, {
                    "type": "typing",
                    "user_id": user_id,
                    "is_typing": True
                })
            
            elif msg_type == "stop_typing":
                target_id = data.get("target_id")
                await manager.send_personal(target_id, {
                    "type": "typing",
                    "user_id": user_id,
                    "is_typing": False
                })
            
            elif msg_type == "read_receipt":
                recipient_id = data.get("recipient_id")
                await manager.send_personal(recipient_id, {
                    "type": "read_receipt",
                    "user_id": user_id,
                    "timestamp": get_current_time()
                })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": get_current_time()})
    
    except WebSocketDisconnect:
        await manager.disconnect_user(user_id)
    except Exception as e:
        print(f"WebSocket error for {user_id}: {e}")
        await manager.disconnect_user(user_id)


# ─── Health Check ─────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "WoeidChat Advanced",
        "version": "2.0",
        "features": ["E2E Encryption", "User Discovery", "Groups (500 max)", "Profiles", "Follow System"]
    }


if __name__ == "__main__":
    print("""
    ════════════════════════════════════════════════════════════
      🔐 WoeidChat Advanced Server v2.0
      Listening on http://0.0.0.0:8765
      Features: Discovery, Groups (500), Profiles, Follow, E2E
    ════════════════════════════════════════════════════════════
    """)
    uvicorn.run(app, host="0.0.0.0", port=8765, log_level="info")
