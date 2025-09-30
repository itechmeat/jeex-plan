# Security Quick Reference

## For Developers

### Authentication

```python
# ✅ CORRECT: Use dependency injection for auth
from app.core.auth import get_current_active_user

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_active_user)
):
    return {"user": current_user.email}

# ❌ WRONG: Manual token parsing
@router.get("/wrong")
async def wrong_route(authorization: str = Header(...)):
    token = authorization.split(" ")[1]  # DON'T DO THIS
```

### Multi-Tenant Data Access

```python
# ✅ CORRECT: Always include tenant_id filter
async def get_projects(db: AsyncSession, tenant_id: str):
    result = await db.execute(
        select(Project).where(Project.tenant_id == tenant_id)
    )
    return result.scalars().all()

# ❌ WRONG: Missing tenant filter
async def get_all_projects(db: AsyncSession):
    result = await db.execute(select(Project))  # DATA LEAK!
    return result.scalars().all()
```

### Password Handling

```python
# ✅ CORRECT: Use password service
from app.core.password_service import PasswordService

password_service = PasswordService()
hashed = await password_service.hash_password("user_password")
is_valid = await password_service.verify_password("user_password", hashed)

# ❌ WRONG: Direct hashing
import hashlib
hashed = hashlib.sha256(password.encode()).hexdigest()  # INSECURE!
```

### Secrets Management

```python
# ✅ CORRECT: Use environment variables + Vault
from app.core.config import Settings

settings = Settings()
api_key = settings.EXTERNAL_API_KEY  # From env/Vault

# ❌ WRONG: Hardcoded secrets
API_KEY = "sk-1234567890abcdef"  # NEVER DO THIS!
```

### Input Validation

```python
# ✅ CORRECT: Pydantic models with validation
from pydantic import BaseModel, EmailStr, validator

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str

    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v

# ❌ WRONG: No validation
def create_user(email: str, username: str, password: str):
    # Direct DB insert without validation
```

## Common Vulnerabilities & Prevention

### SQL Injection

```python
# ✅ CORRECT: Parameterized queries
result = await db.execute(
    select(User).where(User.email == email)
)

# ❌ WRONG: String concatenation
query = f"SELECT * FROM users WHERE email = '{email}'"  # VULNERABLE!
```

### XSS Prevention

```python
# ✅ CORRECT: Return Pydantic models (auto-escaped)
class UserResponse(BaseModel):
    username: str
    email: str

@router.get("/user", response_model=UserResponse)
async def get_user():
    return UserResponse(username=user.username, email=user.email)

# ❌ WRONG: Raw HTML in response
return f"<div>{user.username}</div>"  # XSS RISK!
```

### CSRF Protection

```python
# ✅ CORRECT: Use CSRF token for cookie-based auth
headers = {
    "X-CSRF-Token": csrf_token,
    "Cookie": f"access_token={token}"
}

# ✅ CORRECT: Use Bearer token (stateless, CSRF-exempt)
headers = {
    "Authorization": f"Bearer {token}"
}

# ❌ WRONG: Cookie auth without CSRF token
headers = {"Cookie": f"access_token={token}"}  # VULNERABLE!
```

### Path Traversal Prevention

```python
# ✅ CORRECT: Validate and sanitize paths
from pathlib import Path

def get_file(filename: str):
    safe_name = Path(filename).name  # Remove directory components
    file_path = UPLOAD_DIR / safe_name
    if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise ValueError("Invalid file path")
    return file_path

# ❌ WRONG: Direct path concatenation
file_path = f"/uploads/{filename}"  # VULNERABLE TO ../../../etc/passwd
```

## Security Checklist

### Before Deployment

- [ ] All secrets moved to environment variables/Vault
- [ ] HTTPS enabled (TLS 1.3)
- [ ] CORS configured with explicit origins
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Database RLS policies active
- [ ] Authentication required on all protected routes
- [ ] Input validation on all endpoints
- [ ] Logging enabled for security events
- [ ] Error messages don't leak sensitive info

### Code Review

- [ ] No hardcoded credentials
- [ ] All database queries use parameterization
- [ ] Tenant isolation enforced
- [ ] Password hashing uses strong algorithm
- [ ] JWT tokens include unique ID (jti)
- [ ] Sensitive data not logged
- [ ] Dependencies up to date
- [ ] Error handling doesn't expose internals

### Testing

- [ ] Authentication tests pass
- [ ] Authorization tests verify tenant isolation
- [ ] Rate limiting works as expected
- [ ] CSRF protection active
- [ ] Input validation rejects malicious input
- [ ] Token blacklist prevents replay
- [ ] Password strength requirements enforced

## Emergency Procedures

### Suspected Token Leak

```bash
# 1. Add to blacklist
redis-cli SADD blacklist:jti:<token_id> <user_id>

# 2. Force user logout
POST /api/v1/auth/logout
Authorization: Bearer <admin_token>
{"user_id": "<affected_user_id>"}

# 3. Rotate secrets if needed
./scripts/rotate-jwt-secret.sh
```

### Rate Limit Attack

```bash
# Block IP temporarily
redis-cli SET "ratelimit:ip:<attacker_ip>:blocked" "1" EX 3600

# Check current rate limit status
redis-cli GET "ratelimit:tenant:<tenant_id>:count"
```

### Data Access Audit

```bash
# Review access logs
docker compose logs api | grep "tenant_id=<suspicious_tenant>"

# Check active sessions
redis-cli KEYS "session:*"
```

## Contact

For security issues: <security@jeex-plan.com>
For urgent matters: Use encrypted communication
