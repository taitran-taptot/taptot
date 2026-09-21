from enum import Enum


class AccessPolicy(str, Enum):
    PUBLIC_READ = "public_read"
    AUTH_READ = "auth_read"
    OWNER = "owner"
    ADMIN = "admin"


SENSITIVE_FIELDS = frozenset({"password_hash", "token_hash"})

# Never writable via generic CRUD create/update (mass-assignment guard).
UPDATE_DENYLIST = frozenset(
    {
        "password_hash",
        "token_hash",
        "role",
        "is_verified",
        "share_token",
        "status",
        "amount_vnd",
        "amount",
        "external_id",
        "provider",
        "plan_id",
        "started_at",
        "ended_at",
        "email_verified_at",
    }
)
