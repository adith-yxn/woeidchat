# 🧪 WoeidChat Premium - Complete Integration Testing Guide

## System Verification Checklist

### ✅ Pre-Launch Validation

Before deploying WoeidChat Premium to production, verify all systems pass these tests.

---

## 1️⃣ Backend Server Tests

### Test 1.1: Server Startup
```bash
# Expected output should show:
python woeidchat_premium_server.py

# ════════════════════════════════════════════════════════════
#   🔐 WoeidChat Premium Server v3.0
#   Listening on http://0.0.0.0:8765
#   Features: Premium, Voice/Video, Stickers, Real-time
# ════════════════════════════════════════════════════════════

✅ Server starts without errors
✅ Database initialized (17 tables created)
✅ WebSocket ready on port 8765
✅ Static files served from /static/
```

**Test Result**: [ ] PASS [ ] FAIL

---

### Test 1.2: Database Initialization
```bash
# Verify SQLite database
sqlite3 woeidchat.db ".tables"

# Expected tables:
# sessions users premium_subscriptions transactions
# stickers_store user_sticker_packs messages groups
# group_messages group_members voice_calls
# notifications follows typing_status reactions messages_attachments
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 2️⃣ Authentication Tests

### Test 2.1: User Registration
```bash
curl -X POST http://localhost:8765/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser1",
    "email": "test@example.com",
    "password": "Test1234",
    "password_hint": "My favorite color",
    "public_key": "test_public_key_123"
  }'

# Expected response:
{
  "success": true,
  "message": "User registered successfully",
  "user_id": "uuid-here"
}
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 2.2: User Login
```bash
curl -X POST http://localhost:8765/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser1",
    "password": "Test1234"
  }'

# Expected response:
{
  "success": true,
  "token": "jwt-token-here",
  "user_id": "uuid-here",
  "premium_tier": "free"
}
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 2.3: Password Recovery
```bash
curl http://localhost:8765/forgot-password?username=testuser1

# Expected response:
{
  "success": true,
  "hint": "My favorite color"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 3️⃣ Premium System Tests

### Test 3.1: Get Premium Tiers
```bash
curl http://localhost:8765/premium/tiers

# Expected response:
{
  "success": true,
  "tiers": {
    "free": {
      "price": 0,
      "max_storage_gb": 1,
      "max_group_size": 100,
      "features": ["basic_chat", "groups_up_to_100", "1_gb_storage"]
    },
    "pro": {
      "price": 299,
      "max_storage_gb": 50,
      "features": [...all pro features...]
    },
    "business": {
      "price": 999,
      "max_storage_gb": 500,
      "features": [...all business features...]
    }
  }
}
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 3.2: Upgrade to Premium
```bash
curl -X POST http://localhost:8765/premium/upgrade \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer JWT_TOKEN_HERE" \
  -d '{
    "tier": "pro",
    "payment_method": "stripe_token"
  }'

# Expected response:
{
  "success": true,
  "message": "Upgraded to pro tier",
  "subscription_id": "sub-uuid",
  "renewal_date": "2025-05-18T00:00:00"
}
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 3.3: Check Premium Status
```bash
curl http://localhost:8765/premium/status \
  -H "Authorization: Bearer JWT_TOKEN_HERE"

# Expected response:
{
  "success": true,
  "tier": "pro",
  "storage_limit_gb": 50,
  "storage_used_gb": 0.2,
  "renewal_date": "2025-05-18",
  "status": "active"
}
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 4️⃣ Real-Time Messaging Tests

### Test 4.1: WebSocket Connection
```javascript
// In browser console or Node.js:
const ws = new WebSocket('ws://localhost:8765/ws/realtime/YOUR_JWT_TOKEN');

ws.onopen = () => {
  console.log('✅ WebSocket connected');
};

ws.onmessage = (event) => {
  console.log('Message:', JSON.parse(event.data));
};

ws.onerror = (error) => {
  console.log('❌ Error:', error);
};
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 4.2: Send Message via WebSocket
```javascript
ws.send(JSON.stringify({
  type: "message",
  recipient_id: "OTHER_USER_ID",
  content: "Hello from test!",
  encrypted: true
}));

// Recipient should see:
// { type: "message", from: "sender_id", content: "...", timestamp: "..." }
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 4.3: Typing Indicator
```javascript
// Sender types
ws.send(JSON.stringify({
  type: "typing",
  target_id: "recipient_id",
  is_typing: true
}));

// Recipient sees: { type: "typing", from: "sender_id", is_typing: true }
// Sender stops typing
ws.send(JSON.stringify({
  type: "typing",
  target_id: "recipient_id",
  is_typing: false
}));
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 5️⃣ Voice/Video Call Tests

### Test 5.1: Initiate Call
```bash
curl -X POST http://localhost:8765/calls/initiate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer JWT_TOKEN" \
  -d '{
    "recipient_id": "OTHER_USER_ID",
    "call_type": "voice"
  }'

# Expected response:
{
  "success": true,
  "call_id": "call-uuid",
  "status": "pending"
}

# Recipient should get WebSocket notification:
# { type: "incoming_call", call_id: "...", call_type: "voice", from: "..." }
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 5.2: Accept Call
```bash
curl -X POST http://localhost:8765/calls/CALL_ID/accept \
  -H "Authorization: Bearer JWT_TOKEN"

# Expected response:
{
  "success": true,
  "status": "active",
  "call_duration_started_at": "2025-04-18T12:00:00"
}
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 5.3: End Call
```bash
curl -X POST http://localhost:8765/calls/CALL_ID/end \
  -H "Authorization: Bearer JWT_TOKEN"

# Expected response:
{
  "success": true,
  "status": "ended",
  "duration_seconds": 120
}

# Verify in database: duration saved correctly
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 6️⃣ Stickers Store Tests

### Test 6.1: Get Stickers Store
```bash
curl http://localhost:8765/stickers/store

# Expected response:
{
  "success": true,
  "stickers": [
    {
      "id": 1,
      "name": "Happy Pack",
      "category": "emotions",
      "price_cents": 99,
      "emoji": "😊"
    },
    // ...more stickers...
  ]
}
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 6.2: Purchase Sticker Pack
```bash
curl -X POST http://localhost:8765/stickers/purchase/1 \
  -H "Authorization: Bearer JWT_TOKEN"

# Expected response:
{
  "success": true,
  "message": "Sticker pack purchased",
  "transaction_id": "txn-uuid"
}

# Verify: user_sticker_packs table updated
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 7️⃣ Frontend Web UI Tests

### Test 7.1: Login Page Loads
```
URL: http://localhost:8765/static/login.html

Visual Checks:
✅ Page loads without errors
✅ Left panel shows "WoeidChat" logo
✅ Features listed (E2E, Calls, Groups, Stickers)
✅ Right panel shows login form
✅ 3 tabs visible: Login, Register, Forgot Password
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 7.2: Register Form
```
1. Click "Register" tab
2. Fill in:
   - Name: "Test User"
   - Email: "test@test.com"
   - Username: "testuser"
   - Password: "Test1234"
   - Hint: "Test hint"
3. Click "Create Account"

Expected: ✅ Success message, auto-redirect to login
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 7.3: Login Form
```
1. Enter username/email
2. Enter password
3. Click "Sign In"

Expected: 
✅ Token saved in localStorage
✅ Redirect to chat page
✅ Chat interface loads
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 7.4: Chat Interface
```
Visual Checks:
✅ Sidebar shows chat list
✅ Center shows empty state
✅ Bottom shows message input
✅ Top shows call buttons (☎️ 📹)
✅ Right shows settings + premium buttons
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 7.5: Premium Modal
```
1. Click ⭐ (Premium button)
2. Modal opens showing:

✅ Free tier: $0/month
✅ Pro tier: $2.99/month
✅ Business tier: $9.99/month
✅ Feature comparisons
✅ Upgrade buttons

3. Click "Upgrade Pro"
4. Payment form appears (demo)
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 8️⃣ Security Tests

### Test 8.1: Password Hashing
```bash
# Register user
# Check database - password should be HASHED, not plaintext

sqlite3 woeidchat.db "SELECT username, password_hash FROM users LIMIT 1;"

# Expected: Password should be ~64 char hex string (not readable)
# Example: a7f3e2d1c9b8a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 8.2: Token-Based Auth
```bash
# Try accessing /premium/status WITHOUT token

curl http://localhost:8765/premium/status

# Expected: 401 Unauthorized
# Should NOT expose user data
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 8.3: CORS Protection
```bash
# Try from different domain
# (e.g., open browser console on example.com and call API)

fetch('http://localhost:8765/auth/login', {
  method: 'POST',
  body: JSON.stringify({...})
})

# Expected: Should work (CORS enabled for localhost dev)
# In production: Restrict to your domain
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 9️⃣ Performance Tests

### Test 9.1: Message Latency
```javascript
// WebSocket message send time
const startTime = Date.now();
ws.send(JSON.stringify({ type: "message", content: "test" }));
// Measure time until server echoes back

// Expected: < 100ms for localhost
// Expected: < 500ms for cloud deployment
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 9.2: Concurrent Connections
```bash
# Simulate multiple users connecting
for i in {1..100}; do
  node client.js &
done

# Expected: Server handles all 100 connections
# Check: ps aux | grep woeidchat_premium_server (should not crash)
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 9.3: Database Query Performance
```bash
# Send 1000 messages quickly
# Time should complete in < 5 seconds

time curl -X POST http://localhost:8765/messages \
  -H "Authorization: Bearer TOKEN" \
  -d '{"content":"test"}' | head -1000
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 🔟 Stress Tests

### Test 10.1: Large File Upload
```bash
# Upload 50MB file
dd if=/dev/zero of=test_50mb.bin bs=1M count=50

curl -X POST http://localhost:8765/messages/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test_50mb.bin"

# Expected: Either succeeds or rejects with clear error
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 10.2: Large Message
```javascript
// Send 100KB message
const largeMessage = "x".repeat(100000);
ws.send(JSON.stringify({
  type: "message",
  content: largeMessage
}));

// Expected: Handled gracefully (accept or reject)
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 10.3: Rapid Messages
```javascript
// Send 100 messages per second
for (let i = 0; i < 100; i++) {
  ws.send(JSON.stringify({
    type: "message",
    content: `Message ${i}`
  }));
}

// Expected: All delivered in order
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 1️⃣1️⃣ Error Handling Tests

### Test 11.1: Invalid Login
```bash
curl -X POST http://localhost:8765/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"nope","password":"wrong"}'

# Expected: 401 Unauthorized (not 500 error)
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 11.2: Duplicate Username
```bash
# Register twice with same username

curl -X POST http://localhost:8765/auth/register \
  -d '{...}'

curl -X POST http://localhost:8765/auth/register \
  -d '{...}'

# Expected: Second request returns 409 Conflict
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 11.3: Expired Token
```bash
# Use old/expired token
curl http://localhost:8765/premium/status \
  -H "Authorization: Bearer EXPIRED_TOKEN"

# Expected: 401 Unauthorized, clear error message
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 1️⃣2️⃣ Database Integrity Tests

### Test 12.1: Transaction Rollback
```bash
# Start transaction
# Upgrade user to Pro
# Simulate payment failure

curl -X POST http://localhost:8765/premium/upgrade \
  -d '{"tier":"pro"}'

# Expected: Database unchanged on failure
# Verify: User still on "free" tier
```

**Test Result**: [ ] PASS [ ] FAIL

### Test 12.2: Constraint Validation
```bash
# Try to insert invalid data directly
sqlite3 woeidchat.db "INSERT INTO users (id) VALUES (NULL);"

# Expected: Constraint error (required fields missing)
```

**Test Result**: [ ] PASS [ ] FAIL

---

## 📊 Test Results Summary

### Scoring (11 Sections × ~3-4 tests = ~40 total)

Count total PASS marks:

- **38-40 PASS**: 🟢 **PRODUCTION READY** - Deploy with confidence!
- **35-37 PASS**: 🟡 **READY WITH CAUTION** - Minor issues to fix
- **30-34 PASS**: 🔴 **NOT READY** - Major issues, test more
- **< 30 PASS**: 🛑 **BLOCKED** - Critical failures, don't deploy

### Total Score: _____ / 40

---

## 🚀 Deployment Readiness

- [ ] All authentication tests pass
- [ ] Premium system verified working
- [ ] Real-time messaging latency acceptable
- [ ] No security issues detected
- [ ] Performance meets expectations
- [ ] Error handling robust
- [ ] Database integrity confirmed

**Ready to Deploy?** [ ] YES [ ] NO

If NO, list blockers:
```
1. ___________________________________
2. ___________________________________
3. ___________________________________
```

---

## 📝 Pre-Launch Checklist

- [ ] Environment variables set (STRIPE_SECRET_KEY)
- [ ] Database backed up
- [ ] Logs configured
- [ ] Monitoring set up
- [ ] Support contact info ready
- [ ] Terms of Service reviewed
- [ ] Privacy policy finalized
- [ ] Backup restore tested
- [ ] Disaster recovery plan ready

---

## 🎯 Sign-Off

**Tester Name**: _____________________

**Date**: _____________________

**Sign-off**: 
- [ ] Approved for production
- [ ] Requires fixes
- [ ] Rejected

**Notes**:
```
_________________________________________________________
_________________________________________________________
_________________________________________________________
```

---

**Version**: 3.0 Premium Testing Guide
**Status**: ✅ Ready
**Last Updated**: Today

🎉 **Congratulations on shipping WoeidChat Premium!**
