# 🎨 WoeidChat Premium - Visual Architecture & Flow Diagrams

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Devices (Client)                       │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Web Browser (Chrome/Firefox/Safari)         │  │
│  │                                                          │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │         Login Page (login.html)                   │ │  │
│  │  │  ┌─────────────────────────────────────────────┐  │ │  │
│  │  │  │ Registration Form                           │  │ │  │
│  │  │  │ - Name, Email, Username                     │  │ │  │
│  │  │  │ - Password (with strength meter)            │  │ │  │
│  │  │  │ - Password Hint (for recovery)              │  │ │  │
│  │  │  └─────────────────────────────────────────────┘  │ │  │
│  │  │                                                    │ │  │
│  │  │  ┌─────────────────────────────────────────────┐  │ │  │
│  │  │  │ Login Form                                  │  │ │  │
│  │  │  │ - Username/Email                            │  │ │  │
│  │  │  │ - Password                                  │  │ │  │
│  │  │  │ - "Remember Me" checkbox                    │  │ │  │
│  │  │  └─────────────────────────────────────────────┘  │ │  │
│  │  │                                                    │ │  │
│  │  │  ┌─────────────────────────────────────────────┐  │ │  │
│  │  │  │ Password Recovery                           │  │ │  │
│  │  │  │ - Enter username                            │  │ │  │
│  │  │  │ - Shows your password hint                  │  │ │  │
│  │  │  └─────────────────────────────────────────────┘  │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │                           ↓                              │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │    Chat Interface (index.html - After Login)      │ │  │
│  │  │                                                   │ │  │
│  │  │  ┌──────────────┐         ┌──────────────────┐  │ │  │
│  │  │  │  Sidebar     │         │  Chat Area       │  │ │  │
│  │  │  │              │         │                  │  │ │  │
│  │  │  │ • Search     │         │ [Contact Name]   │  │ │  │
│  │  │  │ • Chat List  │         │ ☎️ 📹          │  │ │  │
│  │  │  │ • Online     │         │                  │  │ │  │
│  │  │  │   Indicators │         │ Messages:        │  │ │  │
│  │  │  │              │         │ • Encrypted ✓    │  │ │  │
│  │  │  │ [Search...]  │         │ • Typing: "..."  │  │ │  │
│  │  │  │              │         │                  │  │ │  │
│  │  │  │ • Alice ✓    │         │ Input: [msg] ➤  │  │ │  │
│  │  │  │ • Tech Team  │         │ 📎 😊           │  │ │  │
│  │  │  │ • Bob ✓      │         └──────────────────┘  │ │  │
│  │  │  └──────────────┘                               │ │  │
│  │  │                 ↓                               │ │  │
│  │  │  Modals (Popups):                               │ │  │
│  │  │  ┌─────────────────────────────────────────┐  │ │  │
│  │  │  │ Premium Store (⭐)                      │  │ │  │
│  │  │  │ • Free: $0 (1GB, 100-person groups)    │  │ │  │
│  │  │  │ • Pro: $2.99 (50GB, 500-person groups) │  │ │  │
│  │  │  │ • Business: $9.99 (500GB, unlimited)   │  │ │  │
│  │  │  │ [Upgrade Pro] [Upgrade Business]       │  │ │  │
│  │  │  └─────────────────────────────────────────┘  │ │  │
│  │  │                                                │ │  │
│  │  │  ┌─────────────────────────────────────────┐  │ │  │
│  │  │  │ Settings (⚙️)                           │  │ │  │
│  │  │  │ • Profile name & status                 │  │ │  │
│  │  │  │ • Notifications on/off                  │  │ │  │
│  │  │  │ • Theme selector                        │  │ │  │
│  │  │  │ [Save Changes]                          │  │ │  │
│  │  │  └─────────────────────────────────────────┘  │ │  │
│  │  │                                                │ │  │
│  │  │  ┌─────────────────────────────────────────┐  │ │  │
│  │  │  │ Stickers Store (😊)                     │  │ │  │
│  │  │  │ • Emoji picker                          │  │ │  │
│  │  │  │ • [Buy Premium Stickers]                │  │ │  │
│  │  │  └─────────────────────────────────────────┘  │ │  │
│  │  │                                                │ │  │
│  │  │  Storage: JWT token in localStorage           │ │  │
│  │  │  WebSocket: ws://localhost:8765/ws/...        │ │  │
│  │  └────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           ↓ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Server                        │
│                   (woeidchat_premium_server.py)                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           REST API Endpoints (30+)                       │  │
│  │                                                          │  │
│  │  Authentication:                                         │  │
│  │  POST /auth/register      → Create user account         │  │
│  │  POST /auth/login         → Authenticate user           │  │
│  │  GET  /forgot-password    → Get password hint           │  │
│  │                                                          │  │
│  │  Premium:                                                │  │
│  │  GET  /premium/tiers      → Get subscription tiers      │  │
│  │  POST /premium/upgrade    → Upgrade to tier            │  │
│  │  GET  /premium/status     → Check current tier          │  │
│  │                                                          │  │
│  │  Stickers:                                               │  │
│  │  GET  /stickers/store     → Get available stickers      │  │
│  │  POST /stickers/purchase  → Purchase sticker pack       │  │
│  │                                                          │  │
│  │  Calls:                                                  │  │
│  │  POST /calls/initiate     → Start call                  │  │
│  │  POST /calls/{id}/accept  → Accept incoming call        │  │
│  │  POST /calls/{id}/end     → End call                    │  │
│  │                                                          │  │
│  │  Admin:                                                  │  │
│  │  GET  /stats              → Analytics & revenue         │  │
│  │  GET  /health             → Server status               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        WebSocket Handler (Real-time)                    │  │
│  │        /ws/realtime/{token}                             │  │
│  │                                                          │  │
│  │  Message Types:                                          │  │
│  │  • "message"        → Direct messages                   │  │
│  │  • "group_message"  → Group chat                        │  │
│  │  • "typing"         → User is typing indicator          │  │
│  │  • "reaction"       → Message reaction                  │  │
│  │  • "incoming_call"  → Call notification                 │  │
│  │  • "presence"       → Online/offline status             │  │
│  │  • "ping/pong"      → Keep-alive heartbeat              │  │
│  │                                                          │  │
│  │  ConnectionManager:                                      │  │
│  │  • Maintains active_users dict (user_id → WebSocket)    │  │
│  │  • Tracks group_connections for broadcasting            │  │
│  │  • Manages typing_status for indicators                 │  │
│  │  • Handles call_sessions for voice/video               │  │
│  │  • Thread-safe with asyncio locks                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │       Business Logic & Encryption Layer                 │  │
│  │                                                          │  │
│  │  Authentication:                                         │  │
│  │  • PBKDF2-SHA256 password hashing (200k iterations)     │  │
│  │  • JWT token generation & validation                    │  │
│  │  • Session management                                   │  │
│  │                                                          │  │
│  │  Encryption:                                             │  │
│  │  • RSA-2048 key exchange                                │  │
│  │  • AES-256-CBC message encryption                       │  │
│  │  • Per-message random IV generation                     │  │
│  │                                                          │  │
│  │  Premium System:                                         │  │
│  │  • Tier enforcement (free/pro/business)                 │  │
│  │  • Feature flags per tier                               │  │
│  │  • Storage limit enforcement                            │  │
│  │  • Group size limits                                    │  │
│  │                                                          │  │
│  │  Payment Processing:                                     │  │
│  │  • Stripe API integration                               │  │
│  │  • Subscription creation & management                   │  │
│  │  • Transaction recording                                │  │
│  │  • Renewal date calculation                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           ↓ SQL Queries
┌─────────────────────────────────────────────────────────────────┐
│              SQLite Database (17 Tables)                        │
│                  woeidchat.db                                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Users & Authentication                        │  │
│  │  • users (user_id, username, email, password_hash...)   │  │
│  │  • sessions (token, user_id, expiry...)                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Messaging & Groups                            │  │
│  │  • messages (message_id, sender_id, recipient_id...)    │  │
│  │  • groups (group_id, name, creator_id, member_count...)│  │
│  │  • group_messages (msg_id, group_id, sender_id...)      │  │
│  │  • group_members (group_id, user_id, role, joined_at...)│ │  │
│  │  • messages_attachments (file_id, message_id, path...) │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Premium & Payments                            │  │
│  │  • premium_subscriptions (sub_id, user_id, tier...)     │  │
│  │  • transactions (txn_id, user_id, amount, date...)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Voice & Video Calls                           │  │
│  │  • voice_calls (call_id, caller_id, recipient_id...)    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            Monetization & Features                       │  │
│  │  • stickers_store (sticker_id, name, price, emoji...)   │  │
│  │  • user_sticker_packs (user_id, sticker_id, date...)    │  │
│  │  • follows (follower_id, following_id...)               │  │
│  │  • typing_status (user_id, target_id, is_typing...)     │  │
│  │  • reactions (reaction_id, message_id, user_id...)      │  │
│  │  • notifications (notif_id, user_id, type, read...)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  File Storage:                                                  │
│  • /uploads/     → User-uploaded files (images, videos)        │
│  • /woeidchat_keys/  → RSA private keys (per user)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Message Flow Diagram

```
┌─────────────┐                                    ┌─────────────┐
│  User A     │                                    │  User B     │
│ (Browser)   │                                    │ (Browser)   │
└──────┬──────┘                                    └──────┬──────┘
       │                                                   │
       │ 1. Types message: "Hello Bob!"                   │
       │                                                   │
       │ 2. Frontend encrypts with Bob's public key       │
       │    - Generates random AES-256 key               │
       │    - Generates random IV                        │
       │    - Encrypts message content                   │
       │    - Encrypts AES key with Bob's RSA public key │
       │                                                   │
       │ 3. WebSocket sends encrypted message to server: │
       │    {                                             │
       │      type: "message",                            │
       │      recipient_id: "bob_uuid",                   │
       │      content: "encrypted_base64_string",         │
       │      iv: "iv_base64_string",                     │
       │      encrypted_key: "rsa_encrypted_string"       │
       │    }                                             │
       │                                                   │
       ├──────────────────────┐                           │
       │                      ↓                           │
       │            ┌─────────────────────┐              │
       │            │  FastAPI Server     │              │
       │            │                     │              │
       │            │ 1. Validate JWT     │              │
       │            │ 2. Check sender     │              │
       │            │ 3. Find Bob's WS    │              │
       │            │ 4. Verify tier      │              │
       │            │ 5. Store in DB      │              │
       │            │ 6. Route message    │              │
       │            └─────────────────────┘              │
       │                      │                          │
       │                      └──────────────────────────┤
       │                                                   │
       │ 4. Bob receives encrypted message via WebSocket:│
       │    {                                             │
       │      type: "message",                            │
       │      from: "alice_uuid",                         │
       │      content: "encrypted_base64_string",         │
       │      encrypted_key: "rsa_encrypted_string",      │
       │      timestamp: "2025-04-18T12:00:00Z"           │
       │    }                                             │
       │                                                   │
       │ 5. Bob's frontend decrypts:                      │
       │    - Finds Bob's private key (localStorage)      │
       │    - Decrypts RSA-encrypted AES key             │
       │    - Decrypts message with AES key + IV         │
       │    - Shows: "Hello Bob!"                         │
       │                                                   │
       │ 6. Bob's frontend sends read receipt:           │
       │    {                                             │
       │      type: "reaction",                           │
       │      message_id: "msg_uuid",                     │
       │      reaction: "✓✓"  (read receipt)             │
       │    }                                             │
       │                                                   │
       │ 7. Alice sees: "Hello Bob!" ✓✓ (read)           │ 7. Bob sees message decrypted ✓✓
       │                                                   │
```

---

## Real-Time Typing Indicator Flow

```
┌─────────────┐                                    ┌─────────────┐
│  User A     │                                    │  User B     │
│ (Typing)    │                                    │ (Watching)  │
└──────┬──────┘                                    └──────┬──────┘
       │                                                   │
       │ 1. User A starts typing                          │
       │    (onkeydown event)                             │
       │                                                   │
       │ 2. WebSocket send:                               │
       │    {                                             │
       │      type: "typing",                             │
       │      target_id: "bob_uuid",                      │
       │      is_typing: true                             │
       │    }                                             │
       │                                                   │
       ├────────────────────→ Server ←──────────────────│
       │                   (validates)                    │
       │                                                   │
       │ 3. Server routes to Bob                          │ 3. Bob receives typing indicator
       │                                                   │    WebSocket message
       │                                                   │
       │                                                   │ 4. Bob's UI shows:
       │                                                   │    "User A is typing..."
       │                                                   │    (with animated dots)
       │                                                   │
       │ 5. User A stops typing                           │
       │    (onkeyup event after 0.5s idle)              │
       │                                                   │
       │ 6. WebSocket send:                               │
       │    {                                             │
       │      type: "typing",                             │
       │      target_id: "bob_uuid",                      │
       │      is_typing: false                            │
       │    }                                             │
       │                                                   │
       ├────────────────────→ Server ←──────────────────│
       │                                                   │
       │                                                   │ 7. Bob's UI updates:
       │                                                   │    Typing indicator disappears
       │                                                   │
```

---

## Voice Call Flow

```
┌─────────────┐                                    ┌─────────────┐
│  User A     │                                    │  User B     │
│ (Caller)    │                                    │ (Recipient) │
└──────┬──────┘                                    └──────┬──────┘
       │                                                   │
       │ 1. User A clicks ☎️ (call button)                │
       │                                                   │
       │ 2. POST /calls/initiate                          │
       │    { recipient_id: "bob_uuid",                  │
       │      call_type: "voice" }                        │
       │                                                   │
       ├──────────────────→ Server ←──────────────────│
       │                                                   │
       │                   Creates:                       │
       │                   • call_id = new UUID           │
       │                   • call_status = "pending"      │
       │                   • started_at = now             │
       │                                                   │
       │                   Sends WebSocket:               │
       │                   {                              │
       │                     type: "incoming_call",       │
       │                     call_id: "call_uuid",        │
       │                     from: "alice_uuid",          │
       │                     call_type: "voice"           │
       │                   }                              │
       │                                                   │
       │                                                   │ 3. Bob receives incoming call
       │                                                   │    Notification pops up
       │                                                   │
       │                                                   │ 4. Bob clicks "Answer"
       │                                                   │
       │                                                   │ 5. POST /calls/{call_id}/accept
       │                                                   │    Updates: call_status = "active"
       │                                                   │
       │ 6. Alice receives: call_status = "active"       │
       │    via WebSocket notification                    │
       │                                                   │
       │ 7. Both devices initiate WebRTC:                 │
       │    (Client-side peer-to-peer connection)         │
       │                                                   │
       │ ═════════ Audio Stream Active ═════════          │
       │           (Direct P2P Connection)                │
       │                                                   │
       │ 8. During call:                                  │
       │    • Duration calculated: now - started_at       │
       │    • Status: "active"                            │
       │    • Keep-alive: ping/pong every 30s             │
       │                                                   │
       │ 9. User A ends call                              │
       │    POST /calls/{call_id}/end                     │
       │                                                   │
       ├──────────────────→ Server ←──────────────────│
       │                                                   │
       │                   Updates:                       │
       │                   • call_status = "ended"        │
       │                   • duration_seconds = elapsed   │
       │                   • ended_at = now               │
       │                                                   │
       │                   Sends WebSocket:               │
       │                   { type: "call_ended",          │
       │                     duration: 120 }             │
       │                                                   │
       │ 10. Both devices:                                │
       │     • Close WebRTC connection                    │
       │     • Update call history                        │
       │     • Show: "Call ended (2:00)"                  │
       │                                                   │
```

---

## Premium Upgrade Flow

```
┌─────────────┐
│  User View  │
└──────┬──────┘
       │
       │ 1. Click ⭐ (Premium button)
       │
       ├─→ Premium Modal Opens
       │   ┌─────────────────────────────┐
       │   │ Free:     $0/month          │
       │   │ Pro:      $2.99/month  ✨   │
       │   │ Business: $9.99/month  👔  │
       │   │                             │
       │   │ [Upgrade Pro]               │
       │   │ [Upgrade Business]          │
       │   └─────────────────────────────┘
       │
       │ 2. Click "Upgrade Pro"
       │
       ├─────────────────────────────────────────────────────────→
       │                                                          │
       │                    Server Side                          │
       │                                                          │
       │   POST /premium/upgrade                                 │
       │   { tier: "pro", payment_method: "stripe_token" }      │
       │                                                          │
       │   ┌──────────────────────────────────────────────────┐ │
       │   │  1. Validate user JWT token                     │ │
       │   │  2. Check user not already Pro/Business         │ │
       │   │  3. Call Stripe API:                            │ │
       │   │     stripe.Subscription.create(                 │ │
       │   │       customer=stripe_customer_id,              │ │
       │   │       items=[{price: "pro_monthly"}],           │ │
       │   │       auto_renew=true                           │ │
       │   │     )                                           │ │
       │   │  4. Stripe charges $2.99 (or declines)          │ │
       │   │  5. If success:                                 │ │
       │   │     ✓ Create premium_subscriptions record       │ │
       │   │     ✓ Update user tier = "pro"                  │ │
       │   │     ✓ Set storage_limit = 50GB                  │ │
       │   │     ✓ Set renewal_date = today + 30 days       │ │
       │   │     ✓ Create transactions record                │ │
       │   │     ✓ Enable all Pro features                   │ │
       │   │     ✓ Return success response                   │ │
       │   │                                                 │ │
       │   │  6. If Stripe declines:                         │ │
       │   │     ✗ Return error: "Card declined"             │ │
       │   │     ✗ Keep user on Free tier                    │ │
       │   └──────────────────────────────────────────────────┘ │
       │                                                          │
       ├─────────────────────────────────────────────────────────←
       │
       │ 3. Frontend receives success response
       │
       │ 4. Update localStorage & UI
       │    ├─→ premium_tier = "pro"
       │    ├─→ storage_limit = 50GB
       │    ├─→ renewal_date = visible in settings
       │    └─→ Pro features enabled (voice, video, stickers)
       │
       │ 5. Show success message:
       │    "✅ Upgraded to Pro! Enjoy unlimited calls, 50GB storage, and more!"
       │
       │ 6. On next login:
       │    ├─→ GET /premium/status
       │    ├─→ Confirms tier = "pro"
       │    └─→ Auto-enables all Pro features
       │
       │ 7. Every 30 days:
       │    ├─→ Server checks renewal_date
       │    ├─→ Auto-charges $2.99 via Stripe
       │    ├─→ Updates renewal_date = today + 30 days
       │    └─→ User stays Pro
       │
```

---

## Database Schema Overview

```
                     ┌─────────────┐
                     │    users    │ (user_id PK)
                     └──────┬──────┘
                            │
                ┌───────────┼───────────┐
                │           │           │
           ┌────┴────┐ ┌────┴────┐ ┌───┴──────┐
           │messages │ │  groups │ │sessions  │
           └────┬────┘ └────┬────┘ └──────────┘
                │           │
           ┌────┴────┐  ┌───┴─────────────┐
           │messages_│  │group_messages   │
           │attachm  │  └───┬─────────────┘
           └─────────┘      │
                      ┌─────┴──────────┐
                      │group_members   │
                      └────────────────┘


          ┌──────────────────────────────────┐
          │    Premium & Payment Tables      │
          └──────────────────────────────────┘
          ┌──────────────────┐
          │premium_subscr    │ (Stripe integration)
          └──────┬───────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────┴──────┐  ┌─────┴────────┐
    │transactions│  │voice_calls   │
    └────────────┘  └──────────────┘


       ┌──────────────────────────────────┐
       │   Social & Features Tables       │
       └──────────────────────────────────┘
       ┌───────────┐  ┌──────────┐
       │follows    │  │reactions │
       └───────────┘  └──────────┘
       
       ┌──────────────────┐
       │stickers_store    │
       └────┬─────────────┘
            │
       ┌────┴──────────────┐
       │user_sticker_packs │
       └───────────────────┘


       ┌──────────────────────────────────┐
       │   Real-time Features Tables      │
       └──────────────────────────────────┘
       ┌────────────────┐  ┌──────────────┐
       │typing_status   │  │notifications │
       └────────────────┘  └──────────────┘
```

---

## Security & Encryption Diagram

```
Message Encryption (E2E):

┌─────────────────────────────────────────────────────────┐
│                   Sender (User A)                       │
│                                                         │
│ 1. Original Message: "Hello Bob!"                      │
│                                                         │
│ 2. Get Recipient's Public Key (from server)            │
│    Example: RSA-2048 public key                         │
│                                                         │
│ 3. Generate encryption keys:                           │
│    - AES-256 key (32 bytes) = random                   │
│    - IV (16 bytes) = random                            │
│                                                         │
│ 4. Encrypt message content:                            │
│    ciphertext = AES-256-CBC(                           │
│      message="Hello Bob!",                             │
│      key=aes_key,                                      │
│      iv=iv                                             │
│    )                                                   │
│    Result: "a7f3e2d1c9b8a6f5e4d3..." (random)         │
│                                                         │
│ 5. Encrypt the AES key:                                │
│    encrypted_key = RSA-2048(                           │
│      key=aes_key + iv,                                │
│      recipient_public_key                             │
│    )                                                   │
│    Result: "xe8d9c7a5..." (RSA encrypted)             │
│                                                         │
│ 6. Send to server:                                     │
│    {                                                   │
│      recipient: "bob",                                │
│      content: "a7f3e2d1..." (AES encrypted)           │
│      encrypted_key: "xe8d9c7a5..." (RSA encrypted)    │
│    }                                                   │
│                                                         │
│    🔐 Server CANNOT read: Only has encrypted content  │
│       and encrypted AES key. Needs Bob's private key! │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              FastAPI Server (Encrypted)                │
│                                                         │
│ Store in Database:                                      │
│ • content: "a7f3e2d1..." (encrypted)                   │
│ • encrypted_key: "xe8d9c7a5..." (encrypted)           │
│                                                         │
│ 🔐 Server never sees plaintext message!                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  Recipient (User B)                     │
│                                                         │
│ 1. Receive encrypted message from server               │
│    {                                                   │
│      content: "a7f3e2d1...",                          │
│      encrypted_key: "xe8d9c7a5..."                    │
│    }                                                   │
│                                                         │
│ 2. Get Bob's Private Key (from localStorage)           │
│    🔐 Private key NEVER leaves device!                 │
│                                                         │
│ 3. Decrypt the AES key:                                │
│    aes_key + iv = RSA-2048-DECRYPT(                    │
│      encrypted_key="xe8d9c7a5...",                    │
│      bob_private_key                                   │
│    )                                                   │
│                                                         │
│ 4. Decrypt message content:                            │
│    plaintext = AES-256-CBC-DECRYPT(                    │
│      ciphertext="a7f3e2d1...",                        │
│      key=aes_key,                                      │
│      iv=iv                                             │
│    )                                                   │
│    Result: "Hello Bob!"                                │
│                                                         │
│ 5. Display to user:                                    │
│    ✅ "Hello Bob!" (decrypted in browser only)        │
│                                                         │
│    🔐 Only Bob can decrypt!                            │
│       Even server couldn't read if it tried!           │
└─────────────────────────────────────────────────────────┘
```

---

## Infrastructure Scaling Diagram

```
┌────────────────────────────────────────────────────────────────┐
│              Development (1 Server)                            │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │   FastAPI Server (localhost:8765)                      │ │
│  │   • Single process                                     │ │
│  │   • SQLite database                                    │ │
│  │   • ~100-1,000 concurrent users                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↓


┌────────────────────────────────────────────────────────────────┐
│          Small Scale (100-1,000 Users)                         │
│          Single VPS or Cloud Instance                          │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Railway / Heroku / DigitalOcean                        │ │
│  │  • FastAPI server (Uvicorn)                             │ │
│  │  • SQLite or PostgreSQL                                 │ │
│  │  • Auto-scaling disabled                                │ │
│  │  • Cost: $5-20/month                                    │ │
│  │  • Users: 1K-10K concurrent                             │ │
│  └─────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
                              ↓


┌────────────────────────────────────────────────────────────────┐
│        Medium Scale (10K-100K Users)                           │
│        Load Balanced Architecture                              │
│                                                                │
│   ┌───────────────────────────────┐                           │
│   │  Load Balancer (nginx)         │                           │
│   │  • Route traffic              │                           │
│   │  • WebSocket sticky sessions  │                           │
│   │  • SSL/TLS termination        │                           │
│   └──────────┬──────────┬─────────┘                           │
│              │          │                                      │
│   ┌──────────┴────┐  ┌──┴──────────┐  ┌─────────────┐        │
│   │FastAPI-1      │  │FastAPI-2    │  │FastAPI-N... │        │
│   │(Process 1)    │  │(Process 2)  │  │(Process N)  │        │
│   └──────────┬────┘  └──┬──────────┘  └─────────────┘        │
│              └────────────┼──────────────────────┐             │
│                           │                      │             │
│              ┌────────────▼────────────┐         │             │
│              │  PostgreSQL Database   │         │             │
│              │  • Replicated          │         │             │
│              │  • Backups             │         │             │
│              │  • Connection pooling  │         │             │
│              └────────────────────────┘         │             │
│                                                  │             │
│              ┌────────────────────────┐         │             │
│              │  Redis Cache           ◄─────────┘             │
│              │  • Session storage     │                       │
│              │  • Rate limiting       │                       │
│              │  • Message queue       │                       │
│              └────────────────────────┘                       │
│                                                                │
│  AWS/GCP/Azure:                                                │
│  • Multi-region deployment                                     │
│  • Cost: $100-500/month                                        │
│  • Users: 10K-100K concurrent                                 │
└────────────────────────────────────────────────────────────────┘
                              ↓


┌────────────────────────────────────────────────────────────────┐
│      Large Scale (100K-1M+ Users)                              │
│      Enterprise Architecture                                   │
│                                                                │
│   ┌───────────────────────────────────────┐                   │
│   │  CloudFront / CDN (Edge Locations)    │                   │
│   │  • Global distribution                │                   │
│   │  • Static asset caching               │                   │
│   │  • DDoS protection                    │                   │
│   └────────┬─────────────────┬────────────┘                   │
│            │                 │                                 │
│   ┌────────▼────────┐  ┌─────▼──────────┐                    │
│   │  US Region      │  │  EU Region     │                    │
│   │  Load Balancer  │  │  Load Balancer │  ... More regions  │
│   └────────┬────────┘  └─────┬──────────┘                    │
│            │                 │                                 │
│      ┌─────▼─────┐      ┌────▼────┐                          │
│      │FastAPI    │      │FastAPI  │                          │
│      │Cluster-1  │      │Cluster-2│  ...                     │
│      └──────┬────┘      └────┬────┘                          │
│             │                │                                 │
│   ┌─────────▼────────────────▼────────┐                      │
│   │  Master PostgreSQL (Write)        │                      │
│   │  • Primary database               │                      │
│   │  • Replication to read replicas   │                      │
│   └─────────────┬──────────────────────┘                      │
│   ┌─────────────▼──────────────────────┐                      │
│   │  Read Replicas (PostgreSQL)        │                      │
│   │  • Regional copies                 │                      │
│   │  • Read-only access                │                      │
│   └────────────────────────────────────┘                      │
│                                                                │
│   ┌──────────────────────────────────┐                       │
│   │  Distributed Redis Cluster       │                       │
│   │  • Session storage               │                       │
│   │  • Message queues                │                       │
│   │  • Rate limiting                 │                       │
│   │  • Caching                       │                       │
│   └──────────────────────────────────┘                       │
│                                                                │
│   ┌──────────────────────────────────┐                       │
│   │  Kafka / RabbitMQ                │                       │
│   │  • Async job processing          │                       │
│   │  • Event streaming               │                       │
│   │  • Message reliability           │                       │
│   └──────────────────────────────────┘                       │
│                                                                │
│   ┌──────────────────────────────────┐                       │
│   │  S3 / Object Storage             │                       │
│   │  • File uploads                  │                       │
│   │  • Backups                       │                       │
│   │  • CDN integration               │                       │
│   └──────────────────────────────────┘                       │
│                                                                │
│   ┌──────────────────────────────────┐                       │
│   │  Monitoring & Analytics          │                       │
│   │  • Prometheus                    │                       │
│   │  • Grafana                       │                       │
│   │  • ELK Stack (logs)              │                       │
│   │  • Sentry (errors)               │                       │
│   └──────────────────────────────────┘                       │
│                                                                │
│  Cost: $1,000-5,000/month                                     │
│  Users: 100K-1M+ concurrent                                   │
│  99.99% uptime SLA                                            │
└────────────────────────────────────────────────────────────────┘
```

---

**Version**: 3.0 Premium Architecture
**Status**: ✅ Production Ready
**Last Updated**: Today

🚀 **Ready to scale from development to enterprise!**
