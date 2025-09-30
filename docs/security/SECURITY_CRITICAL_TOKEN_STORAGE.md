# Critical Token Storage Security

## Overview

This document describes the security-critical implementation of token storage and authentication in JEEX Plan.

## Token Storage Strategy

### Access Tokens

- **Storage**: HttpOnly cookies + Authorization header support
- **Lifetime**: 15 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Transmission**: HTTPS only in production
- **Protection**: CSRF tokens for cookie-based auth

### Refresh Tokens

- **Storage**: HttpOnly cookies only (never exposed to JavaScript)
- **Lifetime**: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- **Rotation**: New refresh token issued on every refresh operation
- **Invalidation**: Blacklist-based revocation on logout

## Security Features

### JWT Security

- **Algorithm**: HS256 with strong secret key (min 32 bytes)
- **Claims**:
  - `jti`: Unique JWT ID for tracking and revocation
  - `sub`: User ID
  - `tenant_id`: Tenant isolation
  - `exp`: Expiration timestamp
  - `iat`: Issued at timestamp
  - `type`: Token type (access/refresh)

### Cookie Security Attributes

```python
httponly=True      # Prevents JavaScript access
secure=True        # HTTPS only in production
samesite="lax"     # CSRF protection
max_age=<lifetime> # Explicit expiration
```

### CSRF Protection

- **Implementation**: Double-submit cookie pattern
- **Bypass**: Stateless API requests (Bearer token + no cookies)
- **Validation**: Required for cookie-based state-changing requests

## Token Blacklist

### Purpose

- Immediate token revocation on logout
- Prevent replay attacks with compromised tokens
- Track active sessions per user

### Implementation

- Redis-based storage with TTL
- Automatic cleanup of expired entries
- Format: `blacklist:jti:<token_id>` = `<user_id>`

## Best Practices

1. **Never** store tokens in localStorage or sessionStorage
2. **Always** use HttpOnly cookies for refresh tokens
3. **Always** validate token signatures server-side
4. **Always** check token blacklist before accepting tokens
5. **Never** log sensitive token data
6. **Always** use HTTPS in production
7. **Always** rotate refresh tokens on use

## Threat Mitigation

| Threat           | Mitigation                                      |
| ---------------- | ----------------------------------------------- |
| XSS              | HttpOnly cookies prevent JavaScript access      |
| CSRF             | Double-submit cookie + SameSite attribute       |
| Token Replay     | JWT uniqueness (jti) + blacklist                |
| Token Theft      | Short-lived access tokens + secure transmission |
| Session Fixation | Token rotation on refresh                       |

## Compliance

- OWASP Top 10 - A02:2021 (Cryptographic Failures)
- OWASP Top 10 - A07:2021 (Identification and Authentication Failures)
- OWASP ASVS v4.0 - Section 3 (Session Management)
