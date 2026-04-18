# 🔒 Security Documentation

## Overview

WoeidChat implements military-grade encryption with industry best practices for secure messaging.

---

## Encryption Architecture

### End-to-End Encryption (E2E)

**Message Flow:**

```
Alice's Client
    ↓ [E2E Encryption]
    ├─ Generate AES-256 key
    ├─ Encrypt message with AES-256-CBC
    ├─ Encrypt AES key with Bob's RSA-2048 public key
    ├─ Send (encrypted_msg, encrypted_key) to server
    
Server (cannot decrypt)
    ↓ [Route message]
    
Bob's Client
    ↓ [E2E Decryption]
    ├─ Decrypt AES key with private RSA-2048 key
    ├─ Decrypt message with AES-256-CBC
    ├─ Display plaintext message
```

### Symmetric Encryption: AES-256-CBC

- **Algorithm**: Advanced Encryption Standard (AES)
- **Key Size**: 256 bits
- **Mode**: Cipher Block Chaining (CBC)
- **IV**: 16-byte random initialization vector
- **Padding**: PKCS7 padding

**Implementation:**
```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

aes_key = secrets.token_bytes(32)  # 256-bit key
iv = secrets.token_bytes(16)        # 128-bit IV
cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
encryptor = cipher.encryptor()
ciphertext = encryptor.update(plaintext) + encryptor.finalize()
```

### Asymmetric Encryption: RSA-2048-OAEP

- **Algorithm**: RSA (Rivest-Shamir-Adleman)
- **Key Size**: 2048 bits
- **Padding**: OAEP (Optimal Asymmetric Encryption Padding)
- **Hash**: SHA-256

**Implementation:**
```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding

private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)
public_key = private_key.public_key()

# Encrypt AES key
encrypted_aes_key = public_key.encrypt(
    aes_key,
    asym_padding.OAEP(
        mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)
```

---

## Authentication & Passwords

### Password Hashing: PBKDF2-SHA256

- **Algorithm**: PBKDF2 (Password-Based Key Derivation Function 2)
- **Hash Function**: SHA-256
- **Iterations**: 200,000
- **Salt**: 32-byte random salt

**Implementation:**
```python
import hashlib

salt = secrets.token_hex(16)
password_hash = hashlib.pbkdf2_hmac(
    'sha256',
    password.encode(),
    salt.encode(),
    200_000
)
```

**Why 200,000 iterations?**
- OWASP recommends ≥100,000 (as of 2023)
- Makes brute-force attacks computationally expensive
- ~100ms to hash on modern hardware
- Adjustable for future hardware improvements

### Token-Based Authentication

- **Token Type**: Bearer Token (JWT-compatible)
- **Token Format**: 64-character hex string (256 bits)
- **Storage**: Secure session table in database
- **Validation**: Server-side verification on each WebSocket connection

```python
token = secrets.token_hex(32)  # 64-char hex string
# Stored in sessions table with username and creation time
```

---

## Transport Security

### WebSocket Secure (WSS)

**For Production:**
- Use `wss://` instead of `ws://`
- Requires TLS/SSL certificate (Let's Encrypt free)
- Enforces encryption at transport layer

**Nginx Configuration:**
```nginx
location /ws {
    proxy_pass http://localhost:8765;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "Upgrade";
    proxy_ssl_verify off;
}
```

### HTTPS/TLS

- **Protocol**: TLS 1.2 or 1.3 (minimum)
- **Certificate**: Let's Encrypt (free, auto-renewing)
- **HSTS**: Enabled (force HTTPS)
- **Cipher Suites**: Strong, modern ciphers

---

## Database Security

### SQLite (Development)

- Single-file database
- No built-in user authentication
- **Not recommended for production**

### PostgreSQL (Production)

```sql
-- Strong user permissions
CREATE USER woeidchat_user WITH PASSWORD 'strong_random_password';
GRANT CONNECT ON DATABASE woeidchat TO woeidchat_user;
GRANT USAGE ON SCHEMA public TO woeidchat_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO woeidchat_user;

-- Row-level security
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation ON messages
    USING ((sender = current_user) OR (recipient = current_user));
```

### Encrypted at Rest

```sql
-- Enable encryption
CREATE EXTENSION pgcrypto;

-- Store sensitive data encrypted
ALTER TABLE users ADD COLUMN email_encrypted bytea;
UPDATE users SET email_encrypted = pgp_pub_encrypt(email, dearmor(pgp_key));
```

---

## File Upload Security

### Validation

```python
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.pdf', '.txt'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Check extension (whitelist approach)
if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
    raise HTTPException(400, "File type not allowed")

# Check file size
if file.size > MAX_FILE_SIZE:
    raise HTTPException(413, "File too large")
```

### File Storage

- Store files outside web root
- Random filenames: `secrets.token_hex(8) + extension`
- MIME type validation
- Virus scanning (optional): ClamAV integration

```python
# Secure filename generation
filename = f"{secrets.token_hex(8)}{ext}"
filepath = Path("uploads") / filename

# Serve with proper headers
@app.get("/uploads/{filename}")
async def serve_file(filename: str):
    # Validate filename format
    if not re.match(r'^[a-f0-9]{16}\.\w+$', filename):
        raise HTTPException(404)
    # Serve file with Content-Disposition
```

---

## API Security

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

# Restrict to specific origins (production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/register")
@limiter.limit("3/minute")  # Max 3 registrations per minute
async def register(request: Request, req: RegisterReq):
    pass
```

### Input Validation

```python
from pydantic import BaseModel, Field, constr

class RegisterReq(BaseModel):
    username: constr(min_length=3, max_length=20, regex=r'^[a-zA-Z0-9_]+$')
    password: constr(min_length=6, max_length=128)
    public_key: str = Field(...)
```

### SQL Injection Prevention

```python
# ✅ SAFE: Parameterized queries
cursor.execute(
    "SELECT * FROM users WHERE username = ?",
    (username,)  # Parameter
)

# ❌ UNSAFE: String concatenation
cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

---

## Key Management

### Key Generation

```python
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(
    public_exponent=65537,      # Standard RSA exponent
    key_size=2048,               # Minimum secure size
    backend=default_backend()
)
```

### Key Storage

**Local Storage (Client):**
- Pickle file with RSA keys
- Location: `woeidchat_keys/{username}.pkl`
- Not encrypted (protect file system)

**Secure Approach for Production:**
```python
from cryptography.hazmat.primitives import serialization

# Encrypt private key before storing
encrypted_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(
        password=b"strong_passphrase"
    )
)
```

### Key Rotation

```python
# Periodic key rotation (recommended annually)
def rotate_keys(username: str, new_public_key: str):
    conn = get_db()
    old_public_key = conn.execute(
        "SELECT public_key FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    
    # Update with new key
    conn.execute(
        "UPDATE users SET public_key = ? WHERE username = ?",
        (new_public_key, username)
    )
    conn.commit()
    
    # Re-encrypt any pending messages with new key
```

---

## Threat Model

### What We Protect Against

| Threat | Protection |
|---|---|
| Eavesdropping | E2E encryption (AES-256 + RSA-2048) |
| Man-in-the-Middle | TLS/SSL + Message authentication |
| Unauthorized Access | Strong password hashing + Tokens |
| SQL Injection | Parameterized queries |
| XSS Attacks | Input validation + Output encoding |
| CSRF | CORS restrictions + Token validation |
| File Upload Attacks | Whitelist + Size limits + Storage outside web root |

### What We Don't Protect Against

- **Local compromises**: Malware on client/server
- **Endpoint vulnerabilities**: Exploits before encryption
- **Metadata**: Server knows participants and timing
- **Social engineering**: Users sharing passwords
- **Quantum computers**: RSA-2048 will eventually be broken

---

## Compliance

### Standards & Certifications

- **OWASP Top 10**: Addresses most vulnerabilities
- **CWE**: Common Weakness Enumeration
- **NIST Guidelines**: Cryptography recommendations

### GDPR Compliance

```python
# Right to deletion
@app.delete("/users/{username}")
async def delete_user(username: str):
    conn = get_db()
    # Delete user data
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.execute("DELETE FROM messages WHERE sender = ? OR recipient = ?", 
                 (username, username))
    conn.commit()
    conn.close()
```

---

## Security Audit Checklist

- [ ] Encryption enabled for all messages
- [ ] SSL/TLS configured for HTTPS
- [ ] Password hashing with PBKDF2 (200k iterations)
- [ ] SQL injection prevention (parameterized queries)
- [ ] CORS restricted to trusted origins
- [ ] Rate limiting enabled
- [ ] File upload validation
- [ ] Session tokens are cryptographically secure
- [ ] Error messages don't leak information
- [ ] Logging doesn't include sensitive data
- [ ] Dependencies updated regularly
- [ ] Security headers set (CSP, HSTS, etc.)
- [ ] Database backups encrypted
- [ ] Secrets not in version control (.env in .gitignore)

---

## Reporting Security Issues

⚠️ **Please don't open public GitHub issues for security vulnerabilities**

Instead:
1. Email: security@woeidchat.com
2. Include: Description, steps to reproduce, impact
3. Allow 48 hours for response
4. Responsible disclosure appreciated

---

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/2023/)
- [NIST SP 800-175B](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-175B.pdf)
- [cryptography.io](https://cryptography.io/) - Python crypto library docs

---

**Version**: 1.0  
**Last Updated**: April 2026  
**Next Review**: April 2027
