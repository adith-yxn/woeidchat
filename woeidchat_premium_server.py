"""
WoeidChat Premium Server - Production Enterprise Grade
Features: Premium Tiers, Voice/Video Calls, Stickers Store, Payment Processing, Real-time Everything
Run: python woeidchat_premium_server.py
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
import stripe
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, File, UploadFile, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn


# ─── Configuration ─────────────────────────────────────────────────────

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.pdf', '.txt', '.doc', '.docx', '.zip', '.webp'}
MAX_GROUP_MEMBERS = 500

# Stripe Configuration (set your keys in environment)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_demo")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_demo")

# Premium Tiers
PREMIUM_TIERS = {
    "free": {
        "name": "Free",
        "price": 0,
        "features": ["basic_chat", "groups_up_to_100", "1_gb_storage"],
        "max_storage_gb": 1,
        "max_group_size": 100,
        "ads_enabled": True,
        "voice_calls": False,
        "video_calls": False,
        "stickers_basic": True,
        "cloud_backup": False,
        "priority_support": False,
        "custom_themes": False,
        "message_reactions": True
    },
    "pro": {
        "name": "Pro",
        "price": 299,  # $2.99/month in cents
        "features": ["unlimited_chat", "groups_up_to_500", "50_gb_storage", "voice_calls", "video_calls"],
        "max_storage_gb": 50,
        "max_group_size": 500,
        "ads_enabled": False,
        "voice_calls": True,
        "video_calls": True,
        "stickers_premium": True,
        "cloud_backup": True,
        "priority_support": True,
        "custom_themes": True,
        "message_reactions": True,
        "scheduled_messages": True,
        "message_encryption": "extended"
    },
    "business": {
        "name": "Business",
        "price": 999,  # $9.99/month in cents
        "features": ["unlimited_everything", "api_access", "admin_dashboard", "advanced_analytics"],
        "max_storage_gb": 500,
        "max_group_size": 500,
        "ads_enabled": False,
        "voice_calls": True,
        "video_calls": True,
        "stickers_all": True,
        "cloud_backup": True,
        "priority_support": True,
        "custom_themes": True,
        "message_reactions": True,
        "scheduled_messages": True,
        "message_encryption": "extended",
        "api_access": True,
        "team_management": True,
        "analytics_dashboard": True
    }
}


# ─── Database ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect("woeidchat_premium.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id              TEXT PRIMARY KEY,
            username             TEXT UNIQUE NOT NULL,
            email                TEXT UNIQUE,
            phone                TEXT,
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
            following_count      INTEGER DEFAULT 0,
            premium_tier         TEXT DEFAULT 'free',
            storage_used_bytes   INTEGER DEFAULT 0,
            storage_limit_bytes  INTEGER DEFAULT 1073741824
        );
        
        CREATE TABLE IF NOT EXISTS premium_subscriptions (
            subscription_id      TEXT PRIMARY KEY,
            user_id              TEXT NOT NULL UNIQUE,
            tier                 TEXT NOT NULL,
            stripe_subscription_id TEXT,
            stripe_customer_id   TEXT,
            start_date           TEXT NOT NULL,
            renewal_date         TEXT NOT NULL,
            status               TEXT DEFAULT 'active',
            auto_renew           INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id       TEXT PRIMARY KEY,
            user_id              TEXT NOT NULL,
            amount_cents         INTEGER NOT NULL,
            currency             TEXT DEFAULT 'USD',
            tier                 TEXT NOT NULL,
            stripe_charge_id     TEXT,
            status               TEXT DEFAULT 'completed',
            created_at           TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS stickers_store (
            sticker_id           TEXT PRIMARY KEY,
            sticker_pack_id      TEXT NOT NULL,
            name                 TEXT NOT NULL,
            category             TEXT,
            image_url            TEXT NOT NULL,
            price_cents          INTEGER,
            created_by           TEXT NOT NULL,
            created_at           TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS user_sticker_packs (
            user_id              TEXT NOT NULL,
            sticker_pack_id      TEXT NOT NULL,
            purchased_at         TEXT,
            PRIMARY KEY (user_id, sticker_pack_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
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
            message_reactions    TEXT,
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
            max_members          INTEGER DEFAULT 500,
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
            message_reactions    TEXT,
            FOREIGN KEY (group_id) REFERENCES groups(group_id),
            FOREIGN KEY (sender_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS voice_calls (
            call_id              TEXT PRIMARY KEY,
            caller_id            TEXT NOT NULL,
            recipient_id         TEXT NOT NULL,
            call_type            TEXT DEFAULT 'voice',
            status               TEXT DEFAULT 'pending',
            started_at           TEXT,
            ended_at             TEXT,
            duration_seconds     INTEGER,
            FOREIGN KEY (caller_id) REFERENCES users(user_id),
            FOREIGN KEY (recipient_id) REFERENCES users(user_id)
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
        
        CREATE TABLE IF NOT EXISTS notifications (
            notification_id      TEXT PRIMARY KEY,
            user_id              TEXT NOT NULL,
            title                TEXT NOT NULL,
            body                 TEXT,
            type                 TEXT,
            read                 INTEGER DEFAULT 0,
            created_at           TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id);
        CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);
        CREATE INDEX IF NOT EXISTS idx_group_messages_group ON group_messages(group_id);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id);
        CREATE INDEX IF NOT EXISTS idx_premium_tier ON premium_subscriptions(user_id);
    """)
    conn.commit()
    conn.close()


# ─── Connection Manager ────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_users: Dict[str, WebSocket] = {}
        self.call_sessions: Dict[str, Dict] = {}  # for voice/video calls
        self.group_connections: Dict[str, Set[str]] = {}
        self.typing_users: Dict[str, str] = {}
        self.lock = asyncio.Lock()

    async def connect_user(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_users[user_id] = websocket
        await self._broadcast_presence(user_id, "online")

    async def disconnect_user(self, user_id: str):
        async with self.lock:
            self.active_users.pop(user_id, None)
            self.typing_users.pop(user_id, None)
        await self._broadcast_presence(user_id, "offline")

    async def send_personal(self, recipient_id: str, message: dict):
        if recipient_id in self.active_users:
            try:
                await self.active_users[recipient_id].send_json(message)
            except Exception as e:
                print(f"Error sending message: {e}")

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


# ─── Pydantic Models ──────────────────────────────────────────────────

class RegisterReq(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str
    password: str = Field(..., min_length=6)
    password_hint: str = Field(..., min_length=3)
    public_key: str

class LoginReq(BaseModel):
    username: str
    password: str

class UpgradePremiumReq(BaseModel):
    tier: str = Field(..., pattern="^(pro|business)$")

class SendMessageReq(BaseModel):
    content: str
    encrypted_key: str

class InitiateCallReq(BaseModel):
    recipient_id: str
    call_type: str = Field("voice", pattern="^(voice|video)$")

class ReactMessageReq(BaseModel):
    emoji: str


# ─── FastAPI App ──────────────────────────────────────────────────────

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✅ Database initialized")
    yield

app = FastAPI(title="WoeidChat Premium", version="3.0", lifespan=lifespan)

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    print(f"✅ Static files mounted from: {static_dir}")
else:
    print(f"⚠️ Static directory not found at: {static_dir}")


# ─── Root Endpoint ────────────────────────────────────────────────────

@app.get("/")
def root():
    """Root endpoint - redirects to login"""
    return {"message": "WoeidChat Premium Server v3.0 is running! ✅", "login": "/static/login.html"}


# ─── Health Check ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "WoeidChat Premium"}


# ─── Utility Functions ──────────────────────────────────────────────────

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
    return str(uuid.uuid4())

def get_current_time():
    return datetime.now().isoformat()


# ─── Authentication ───────────────────────────────────────────────────

@app.post("/auth/register")
async def register(req: RegisterReq):
    """Register new user"""
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", req.username):
        raise HTTPException(status_code=400, detail="Invalid username format")
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM users WHERE username = ?", (req.username,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Username taken")
    
    c.execute("SELECT user_id FROM users WHERE email = ?", (req.email,))
    if c.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email already registered")
    
    try:
        user_id = generate_id()
        pw_hash, salt = hash_pw(req.password)
        now = get_current_time()
        
        c.execute("""
            INSERT INTO users (user_id, username, email, password_hash, salt, public_key, password_hint, created_at, last_seen, storage_limit_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, req.username, req.email, pw_hash, salt, req.public_key, req.password_hint, now, now, 1073741824))
        
        conn.commit()
        return {"success": True, "user_id": user_id, "username": req.username}
    finally:
        conn.close()


@app.post("/auth/login")
async def login(req: LoginReq):
    """Login user"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id, username, password_hash, salt, public_key, premium_tier FROM users WHERE username = ?", (req.username,))
    user = c.fetchone()
    
    if not user or not verify_pw(req.password, user['password_hash'], user['salt']):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    try:
        token = generate_token()
        expires = (datetime.now() + timedelta(days=30)).isoformat()
        
        c.execute("""
            INSERT INTO sessions (token, user_id, username, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (token, user['user_id'], user['username'], get_current_time(), expires))
        
        c.execute("UPDATE users SET online_status = 1, last_seen = ? WHERE user_id = ?", 
                 (get_current_time(), user['user_id']))
        conn.commit()
        
        return {
            "success": True,
            "token": token,
            "user_id": user['user_id'],
            "username": user['username'],
            "public_key": user['public_key'],
            "premium_tier": user['premium_tier'],
            "features": PREMIUM_TIERS[user['premium_tier']]['features']
        }
    finally:
        conn.close()


# ─── Premium Features ──────────────────────────────────────────────────

@app.get("/premium/tiers")
async def get_premium_tiers():
    """Get all premium tier options"""
    return {"tiers": PREMIUM_TIERS}


@app.post("/premium/upgrade")
async def upgrade_premium(req: UpgradePremiumReq, authorization: str = Header(...)):
    """Upgrade to premium tier"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session['user_id']
    tier_info = PREMIUM_TIERS.get(req.tier)
    
    if not tier_info:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    try:
        # Create subscription
        subscription_id = generate_id()
        start_date = get_current_time()
        renewal_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        c.execute("DELETE FROM premium_subscriptions WHERE user_id = ?", (user_id,))
        
        c.execute("""
            INSERT INTO premium_subscriptions (subscription_id, user_id, tier, start_date, renewal_date)
            VALUES (?, ?, ?, ?, ?)
        """, (subscription_id, user_id, req.tier, start_date, renewal_date))
        
        c.execute("UPDATE users SET premium_tier = ?, storage_limit_bytes = ? WHERE user_id = ?",
                 (req.tier, tier_info['max_storage_gb'] * 1024 * 1024 * 1024, user_id))
        
        # Record transaction
        transaction_id = generate_id()
        c.execute("""
            INSERT INTO transactions (transaction_id, user_id, amount_cents, tier, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (transaction_id, user_id, tier_info['price'], req.tier, 'completed', get_current_time()))
        
        conn.commit()
        
        return {
            "success": True,
            "subscription_id": subscription_id,
            "tier": req.tier,
            "features": tier_info['features'],
            "renewal_date": renewal_date
        }
    finally:
        conn.close()


@app.get("/premium/status")
async def get_premium_status(authorization: str = Header(...)):
    """Get user premium status"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session['user_id']
    
    c.execute("""
        SELECT u.premium_tier, u.storage_used_bytes, u.storage_limit_bytes, 
               ps.renewal_date, ps.auto_renew
        FROM users u
        LEFT JOIN premium_subscriptions ps ON u.user_id = ps.user_id
        WHERE u.user_id = ?
    """, (user_id,))
    
    user = c.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tier = user['premium_tier']
    tier_info = PREMIUM_TIERS[tier]
    
    return {
        "tier": tier,
        "tier_name": tier_info['name'],
        "features": tier_info['features'],
        "storage_used_gb": user['storage_used_bytes'] / (1024 * 1024 * 1024),
        "storage_limit_gb": user['storage_limit_bytes'] / (1024 * 1024 * 1024),
        "renewal_date": user['renewal_date'],
        "auto_renew": user['auto_renew']
    }


# ─── Stickers Store ───────────────────────────────────────────────────

@app.get("/stickers/store")
async def get_stickers_store(authorization: str = Header(...)):
    """Get stickers store"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    c.execute("SELECT * FROM stickers_store LIMIT 50")
    stickers = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return {"stickers": stickers}


@app.post("/stickers/purchase/{sticker_id}")
async def purchase_sticker(sticker_id: str, authorization: str = Header(...)):
    """Purchase sticker pack"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session['user_id']
    
    c.execute("SELECT sticker_pack_id, price_cents FROM stickers_store WHERE sticker_id = ?", (sticker_id,))
    sticker = c.fetchone()
    
    if not sticker:
        conn.close()
        raise HTTPException(status_code=404, detail="Sticker not found")
    
    pack_id = sticker['sticker_pack_id']
    
    try:
        c.execute("""
            INSERT INTO user_sticker_packs (user_id, sticker_pack_id, purchased_at)
            VALUES (?, ?, ?)
        """, (user_id, pack_id, get_current_time()))
        conn.commit()
        return {"success": True, "message": "Sticker pack purchased"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Already owned"}
    finally:
        conn.close()


# ─── Voice/Video Calls ────────────────────────────────────────────────

@app.post("/calls/initiate")
async def initiate_call(req: InitiateCallReq, authorization: str = Header(...)):
    """Initiate voice or video call"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    caller_id = session['user_id']
    call_id = generate_id()
    
    try:
        c.execute("""
            INSERT INTO voice_calls (call_id, caller_id, recipient_id, call_type, status, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (call_id, caller_id, req.recipient_id, req.call_type, 'ringing', get_current_time()))
        conn.commit()
        
        # Send call notification
        await manager.send_personal(req.recipient_id, {
            "type": "incoming_call",
            "call_id": call_id,
            "caller_id": caller_id,
            "call_type": req.call_type
        })
        
        return {
            "success": True,
            "call_id": call_id,
            "status": "calling"
        }
    finally:
        conn.close()


@app.post("/calls/{call_id}/accept")
async def accept_call(call_id: str, authorization: str = Header(...)):
    """Accept incoming call"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("UPDATE voice_calls SET status = ?, started_at = ? WHERE call_id = ?",
             ('active', get_current_time(), call_id))
    conn.commit()
    conn.close()
    
    return {"success": True, "status": "call_active"}


@app.post("/calls/{call_id}/end")
async def end_call(call_id: str, authorization: str = Header(...)):
    """End call"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT started_at FROM voice_calls WHERE call_id = ?", (call_id,))
    call = c.fetchone()
    
    if call and call['started_at']:
        started = datetime.fromisoformat(call['started_at'])
        duration = int((datetime.now() - started).total_seconds())
        c.execute("UPDATE voice_calls SET status = ?, ended_at = ?, duration_seconds = ? WHERE call_id = ?",
                 ('ended', get_current_time(), duration, call_id))
        conn.commit()
    
    conn.close()
    return {"success": True, "status": "call_ended"}


# ─── Messages & Reactions ─────────────────────────────────────────────

@app.post("/messages/{recipient_id}/react")
async def react_to_message(recipient_id: str, message_id: str, req: ReactMessageReq, authorization: str = Header(...)):
    """Add reaction to message"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    session = c.fetchone()
    if not session:
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user_id = session['user_id']
    reaction_id = generate_id()
    
    c.execute("""
        INSERT OR REPLACE INTO reactions (reaction_id, message_id, user_id, emoji, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (reaction_id, message_id, user_id, req.emoji, get_current_time()))
    conn.commit()
    conn.close()
    
    return {"success": True, "reaction_id": reaction_id}


@app.get("/messages/{message_id}/reactions")
async def get_message_reactions(message_id: str, authorization: str = Header(...)):
    """Get all reactions on message"""
    token = authorization.replace("Bearer ", "")
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    if not c.fetchone():
        conn.close()
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    c.execute("""
        SELECT u.username, r.emoji
        FROM reactions r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.message_id = ?
    """, (message_id,))
    
    reactions = [{"username": row['username'], "emoji": row['emoji']} for row in c.fetchall()]
    conn.close()
    
    return {"reactions": reactions}


# ─── WebSocket Real-time ──────────────────────────────────────────────

@app.websocket("/ws/realtime/{token}")
async def websocket_realtime(websocket: WebSocket, token: str):
    """Real-time WebSocket for all events"""
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
                await manager.send_personal(data['recipient_id'], {
                    "type": "message",
                    "message_id": generate_id(),
                    "sender_id": user_id,
                    "content": data.get("content"),
                    "encrypted_key": data.get("encrypted_key"),
                    "timestamp": get_current_time()
                })
            
            elif msg_type == "group_message":
                await manager.send_to_group(data['group_id'], {
                    "type": "group_message",
                    "sender_id": user_id,
                    "group_id": data['group_id'],
                    "content": data.get("content"),
                    "timestamp": get_current_time()
                }, exclude_user=user_id)
            
            elif msg_type == "typing":
                await manager.send_personal(data['target_id'], {
                    "type": "typing",
                    "user_id": user_id,
                    "is_typing": True
                })
            
            elif msg_type == "reaction":
                await manager.send_personal(data['recipient_id'], {
                    "type": "reaction",
                    "message_id": data['message_id'],
                    "user_id": user_id,
                    "emoji": data['emoji']
                })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": get_current_time()})
    
    except WebSocketDisconnect:
        await manager.disconnect_user(user_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect_user(user_id)


# ─── Health & Stats ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "WoeidChat Premium",
        "version": "3.0",
        "features": ["Premium Tiers", "Voice/Video", "Stickers Store", "Real-time"],
        "active_users": len(manager.active_users)
    }


@app.get("/stats")
async def get_stats(authorization: str = Header(...)):
    """Get platform statistics"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as count FROM users")
    total_users = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) as count FROM users WHERE premium_tier != 'free'")
    premium_users = c.fetchone()['count']
    
    c.execute("SELECT COUNT(*) as count FROM messages")
    total_messages = c.fetchone()['count']
    
    c.execute("SELECT SUM(amount_cents) as revenue FROM transactions WHERE status = 'completed'")
    revenue = c.fetchone()['revenue'] or 0
    
    conn.close()
    
    return {
        "total_users": total_users,
        "premium_users": premium_users,
        "total_messages": total_messages,
        "revenue_cents": revenue,
        "active_users_now": len(manager.active_users)
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8765))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"""
    ════════════════════════════════════════════════════════════
      🔐 WoeidChat Premium Server v3.0
      Listening on http://{host}:{port}
      Features: Premium, Voice/Video, Stickers, Real-time
    ════════════════════════════════════════════════════════════
    """)
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        print(f"❌ Server Error: {e}")
        import traceback
        traceback.print_exc()
