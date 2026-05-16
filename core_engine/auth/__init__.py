"""Authentication primitives for EXPERT_SMART.

Wave S2 (foundation):
- Token generation + verification (HS256)
- Middleware in bridge_api reads tokens silently (no enforcement)

Future waves:
- S3: endpoint-level enforcement
- S4: rate limiting
- S5: audit logging
"""
from core_engine.auth.tokens import AuthError, generate_token, verify_token

__all__ = ["AuthError", "generate_token", "verify_token"]
