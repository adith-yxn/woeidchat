# Contributing to WoeidChat

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- No harassment or discrimination
- Constructive feedback only
- Report violations to: conduct@woeidchat.com

## Getting Started

### 1. Fork & Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/yourusername/woeidchat.git
cd woeidchat
git remote add upstream https://github.com/original-repo/woeidchat.git
```

### 2. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Setup Development Environment

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

### 4. Make Changes

```bash
# Write code following style guide
# Add tests for new features
# Update documentation
```

### 5. Run Tests & Linting

```bash
pytest tests/ -v
flake8 woeidchat_*.py --max-line-length=100
black woeidchat_*.py --line-length=100
mypy woeidchat_*.py
```

### 6. Commit with Clear Message

```bash
git add .
git commit -m "feat: add user profile pictures"
# or
git commit -m "fix: resolve typo in authentication"
# or
git commit -m "docs: update deployment guide"
```

### 7. Push & Create PR

```bash
git push origin feature/your-feature-name
# Then create Pull Request on GitHub
```

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body

footer
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Test additions
- `chore`: Maintenance

**Examples:**
```
feat(messages): add message reactions support

fix(encryption): resolve CBC padding issue

docs(deployment): add AWS EC2 guide

refactor(database): optimize query performance
```

## Pull Request Process

1. **Describe changes** - Clear PR title and description
2. **Link issues** - `Closes #123` in PR description
3. **Keep it focused** - One feature per PR
4. **Update docs** - README, SECURITY, DEPLOYMENT if needed
5. **Add tests** - Maintain >80% code coverage
6. **Pass CI/CD** - All checks must pass
7. **Request review** - Tag maintainers for feedback
8. **Address feedback** - Respond to reviewer comments
9. **Squash commits** - Clean history before merge

## Coding Standards

### Python Style

```python
# Follow PEP 8
# Use type hints
def encrypt_message(message: str, pub_key: str) -> tuple[str, str]:
    """Encrypt message with public key.
    
    Args:
        message: Plaintext message
        pub_key: Recipient's public key (PEM format)
        
    Returns:
        Tuple of (encrypted_content, encrypted_key)
        
    Raises:
        ValueError: If encryption fails
    """
    pass

# Max line length: 100 characters
# 4 spaces indentation
# Double quotes for strings
```

### Code Organization

```
woeidchat/
├── woeidchat_server_enhanced.py
│   ├── Imports
│   ├── Configuration
│   ├── Database setup
│   ├── Authentication
│   ├── API endpoints
│   ├── WebSocket handler
│   └── Main
├── woeidchat_client_enhanced.py
│   ├── Imports
│   ├── Configuration/Theme
│   ├── Encryption class
│   ├── WebSocket worker
│   ├── API client
│   ├── UI classes
│   └── Main
```

## Testing

### Unit Tests

```python
import pytest
from woeidchat_server_enhanced import hash_pw

def test_password_hashing():
    salt = "test_salt_123"
    password = "mypassword"
    hash1 = hash_pw(password, salt)
    hash2 = hash_pw(password, salt)
    
    assert hash1 == hash2  # Deterministic
    assert len(hash1) > 0

def test_invalid_username():
    with pytest.raises(HTTPException):
        # Test invalid username registration
        pass
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_message_delivery():
    # Test end-to-end message flow
    pass
```

### Run Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=woeidchat --cov-report=html

# Specific test
pytest tests/test_encryption.py::test_rsa_encryption -v

# Watch mode (requires pytest-watch)
ptw tests/
```

## Documentation

### Code Comments

```python
# Bad
x = encrypt(msg, key)  # encrypt message

# Good
encrypted_msg = encrypt_message(plaintext, recipient_pub_key)
```

### Docstrings

```python
def register_user(username: str, password: str, public_key: str) -> dict:
    """Register a new user account.
    
    Args:
        username: User's login name (3-20 alphanumeric characters)
        password: User's password (minimum 6 characters)
        public_key: User's RSA public key in PEM format
        
    Returns:
        Dictionary with 'message' and 'username' keys
        
    Raises:
        HTTPException(400): If username/password validation fails
        HTTPException(400): If username already taken
    """
```

### README Updates

When making feature changes:
1. Update feature list in README
2. Add usage examples
3. Update architecture diagram if needed

## Reporting Issues

### Bug Reports

Include:
- [ ] Description of the bug
- [ ] Steps to reproduce
- [ ] Expected behavior
- [ ] Actual behavior
- [ ] Python version & OS
- [ ] Error logs/traceback

### Feature Requests

Include:
- [ ] Clear problem statement
- [ ] Proposed solution
- [ ] Alternative approaches considered
- [ ] Use cases

## Review Process

1. **Automated checks** - CI/CD pipeline validates code
2. **Code review** - Maintainers review for quality
3. **Testing** - Verify tests pass
4. **Documentation** - Check docs are updated
5. **Merge** - Approved PRs are merged to main

## Development Tips

### Debug Mode

```bash
# Server with verbose logging
python woeidchat_server_enhanced.py --debug

# Client with debug output
PYTHONUNBUFFERED=1 python woeidchat_client_enhanced.py
```

### Database Inspection

```bash
sqlite3 woeidchat.db

# View users
SELECT username, created_at FROM users;

# View recent messages
SELECT sender, recipient, timestamp FROM messages LIMIT 10;

# Clear all (dev only!)
DELETE FROM messages;
```

### Testing Encryption

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from woeidchat_client_enhanced import E2EEncryption

enc = E2EEncryption()
enc.generate_keys()

msg = "Hello, World!"
pub_key_pem = enc.get_public_key_pem()
encrypted, key = enc.encrypt(msg, pub_key_pem)
decrypted = enc.decrypt(encrypted, key)

assert decrypted == msg
```

## Release Process

1. Create release branch: `release/v2.0.0`
2. Update version in code and docs
3. Update CHANGELOG.md
4. Create git tag: `git tag v2.0.0`
5. Push tag: `git push origin v2.0.0`
6. Create GitHub release with notes

## Project Structure

```
woeidchat/
├── README.md              # Main documentation
├── CONTRIBUTING.md        # This file
├── DEPLOYMENT.md          # Deployment guides
├── SECURITY.md            # Security info
├── LICENSE                # MIT License
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── woeidchat_server_enhanced.py
├── woeidchat_client_enhanced.py
├── tests/
│   ├── test_encryption.py
│   ├── test_auth.py
│   └── test_messages.py
└── docs/
    ├── api.md
    ├── architecture.md
    └── troubleshooting.md
```

## Roadmap

See [GitHub Projects](https://github.com/yourusername/woeidchat/projects) for planned features.

## Support

- **Questions**: Open GitHub Discussion
- **Bugs**: Open GitHub Issue
- **Security**: Email security@woeidchat.com
- **Chat**: Discord community (link)

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributors page

---

Thank you for contributing to WoeidChat! 🎉
